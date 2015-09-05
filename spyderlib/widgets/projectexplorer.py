# -*- coding: utf-8 -*-
#
# Copyright © 2010-2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Project Explorer"""

# pylint: disable=C0103

from __future__ import print_function

from spyderlib.qt.QtGui import (QVBoxLayout, QLabel, QHBoxLayout, QWidget,
                                QFileIconProvider, QMessageBox, QInputDialog,
                                QLineEdit, QPushButton, QHeaderView,
                                QAbstractItemView)
from spyderlib.qt.QtCore import Qt, SIGNAL, QFileInfo, Slot, Signal
from spyderlib.qt.compat import getexistingdirectory

import os
import re
import shutil
import os.path as osp
import xml.etree.ElementTree as ElementTree

# Local imports
from spyderlib.utils import misc
from spyderlib.utils.qthelpers import get_icon, get_std_icon, create_action
from spyderlib.baseconfig import _, STDERR, get_image_path
from spyderlib.widgets.explorer import FilteredDirView, listdir, fixpath
from spyderlib.widgets.formlayout import fedit
from spyderlib.widgets.pathmanager import PathManager
from spyderlib.py3compat import to_text_string, getcwd, pickle


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
        return get_std_icon('DriveHDIcon')
    prefix = 'pp_' if dirname in project.get_pythonpath() else ''
    if dirname == project.root_path:
        if project.is_opened():
            return get_icon(prefix+'project.png')
        else:
            return get_icon('project_closed.png')
    elif osp.isfile(osp.join(dirname, '__init__.py')):
        return get_icon(prefix+'package.png')
    else:
        return get_icon(prefix+'folder.png')


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
                project = self.treeview.get_source_project(fname)
                if project is None:
                    return super(IconProvider, self).icon(qfileinfo)
                else:
                    return get_dir_icon(fname, project)
            else:
                ext = osp.splitext(fname)[1][1:]
                icon_path = get_image_path(ext+'.png', default=None)
                if icon_path is not None:
                    return get_icon(icon_path)
                else:
                    return super(IconProvider, self).icon(qfileinfo)


class ExplorerTreeWidget(FilteredDirView):
    """Explorer tree widget
    
    workspace: this is the explorer tree widget root path
    (this attribute name is specific to project explorer)"""
    def __init__(self, parent, show_hscrollbar=True):
        FilteredDirView.__init__(self, parent)
        
        self.workspace = Workspace()
        
        self.connect(self.fsmodel, SIGNAL('modelReset()'),
                     self.reset_icon_provider)
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

    def create_file_new_actions(self, fnames):
        """Return actions for submenu 'New...'"""
        new_project_act = create_action(self, text=_('Project...'),
                                        icon=get_icon('project_expanded.png'),
                                        triggered=self.new_project)
        if self.workspace.is_empty():
            new_project_act.setText(_('New project...'))
            return [new_project_act]
        else:
            new_actions = FilteredDirView.create_file_new_actions(self, fnames)
            return [new_project_act, None]+new_actions
        
    def create_file_import_actions(self, fnames):
        """Return actions for submenu 'Import...'"""
        import_folder_act = create_action(self,
                                text=_('Existing directory'),
                                icon=get_std_icon('DirOpenIcon'),
                                triggered=self.import_existing_directory)
        import_spyder_act = create_action(self,
                                text=_('Existing Spyder project'),
                                icon=get_icon('spyder.svg'),
                                triggered=self.import_existing_project)
        import_pydev_act = create_action(self,
                                text=_('Existing Pydev project'),
                                icon=get_icon('pydev.png'),
                                triggered=self.import_existing_pydev_project)
        return [import_folder_act, import_spyder_act, import_pydev_act]
        
    def create_file_manage_actions(self, fnames):
        """Reimplement DirView method"""
        only_folders = all([osp.isdir(_fn) for _fn in fnames])
        projects = [self.get_source_project(fname) for fname in fnames]
        pjfnames = list(zip(projects, fnames))
        any_project = any([_pr.is_root_path(_fn) for _pr, _fn in pjfnames])
        any_folder_in_path = any([_proj.is_in_pythonpath(_fn)
                                  for _proj, _fn in pjfnames])
        any_folder_not_in_path = only_folders and \
                                 any([not _proj.is_in_pythonpath(_fn)
                                      for _proj, _fn in pjfnames])
        open_act = create_action(self,
                            text=_('Open project'),
                            icon=get_icon('project_expanded.png'),
                            triggered=lambda:
                            self.open_projects(projects))
        close_act = create_action(self,
                            text=_('Close project'),
                            icon=get_icon('project_closed.png'),
                            triggered=lambda:
                            self.close_projects(projects))
        close_unrelated_act = create_action(self,
                            text=_('Close unrelated projects'),
                            triggered=lambda:
                            self.close_unrelated_projects(projects))
        manage_path_act = create_action(self,
                            icon=get_icon('pythonpath.png'),
                            text=_('PYTHONPATH manager'),
                            triggered=lambda:
                            self.manage_path(projects))
        relproj_act = create_action(self,
                            text=_('Edit related projects'),
                            triggered=lambda:
                            self.edit_related_projects(projects))
        state = self.workspace is not None\
                and len(self.workspace.projects) > 1
        relproj_act.setEnabled(state)
                    
        add_to_path_act = create_action(self,
                            text=_('Add to PYTHONPATH'),
                            icon=get_icon('add_to_path.png'),
                            triggered=lambda:
                            self.add_to_path(fnames))
        remove_from_path_act = create_action(self,
                            text=_('Remove from PYTHONPATH'),
                            icon=get_icon('remove_from_path.png'),
                            triggered=lambda:
                            self.remove_from_path(fnames))
        properties_act = create_action(self,
                            text=_('Properties'),
                            icon=get_icon('advanced.png'),
                            triggered=lambda:
                            self.show_properties(fnames))

        actions = []
        if any_project:
            if any([not _proj.is_opened() for _proj in projects]):
                actions += [open_act]
            if any([_proj.is_opened() for _proj in projects]):
                actions += [close_act, close_unrelated_act]
            actions += [manage_path_act, relproj_act, None]
        
        if only_folders:
            if any_folder_not_in_path:
                actions += [add_to_path_act]
            if any_folder_in_path:
                actions += [remove_from_path_act]
        actions += [None, properties_act, None]
        actions += FilteredDirView.create_file_manage_actions(self, fnames)
        return actions
        
    def create_context_menu_actions(self):
        """Reimplement DirView method"""
        if self.workspace.is_valid():
            # Workspace's root path is already defined
            return FilteredDirView.create_context_menu_actions(self)
        else:
            return []

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
    def toggle_hscrollbar(self, checked):
        """Toggle horizontal scrollbar"""
        self.parent_widget.sig_option_changed.emit('show_hscrollbar', checked)
        self.show_hscrollbar = checked
        self.header().setStretchLastSection(not checked)
        self.header().setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.header().setResizeMode(QHeaderView.ResizeToContents)
        
    def set_folder_names(self, folder_names):
        """Set folder names"""
        self.setUpdatesEnabled(False)
        FilteredDirView.set_folder_names(self, folder_names)
        self.reset_icon_provider()
        self.setUpdatesEnabled(True)
        
    def reset_icon_provider(self):
        """Reset file system model icon provider
        The purpose of this is to refresh files/directories icons"""
        self.fsmodel.setIconProvider(IconProvider(self))

    def check_for_io_errors(self):
        """Eventually show a warning message box if IOError exception was
        raised when loading/saving the workspace or one of its projects"""
        txt = self.workspace.get_ioerror_warning_message()
        if txt:
            QMessageBox.critical(self, _('Workspace'),
                    _("The workspace was unable to load or save %s<br><br>"
                      "Please check if you have the permission to write the "
                      "associated configuration files.") % txt)
        
    def set_workspace(self, root_path):
        """Set project explorer's workspace directory"""
        self.workspace = Workspace()
        self.setModel(None)
        self.fsmodel = None
        self.proxymodel = None
        self.setup_fs_model()
        self.setup_proxy_model()
        self.workspace.set_root_path(root_path)
        self.set_root_path(root_path)
        for index in range(1, self.model().columnCount()):
            self.hideColumn(index)
        self.set_folder_names(self.workspace.get_folder_names())

        # The following fixes Issue 952: if we don't reset the "show all" 
        # option here, we will lose the feature because we have just rebuilt 
        # the fsmodel object from scratch. This would happen in particular 
        # when setting the workspace option in the project explorer widget
        # (see spyderlib/widgets/projectexplorer.py).
        self.set_show_all(self.show_all)

        self.parent_widget.emit(SIGNAL("pythonpath_changed()"))
#        print "folders:", self.workspace.get_folder_names()
#        print "is_valid:", self.workspace.is_valid()
#        print "is_empty:", self.workspace.is_empty()
        
    def get_workspace(self):
        """Return project explorer's workspace directory"""
        return self.workspace.root_path
    
    def is_in_workspace(self, fname):
        """Return True if file/directory is in workspace"""
        return self.workspace.is_file_in_workspace(fname)
    
    def get_project_path_from_name(self, name):
        """Return project root path from name, knowing the workspace path"""
        return osp.join(self.get_workspace(), name)

    def get_source_project(self, fname):
        """Return project which contains source *fname*"""
        return self.workspace.get_source_project(fname)
        
    def get_project_from_name(self, name):
        """Return project's object from name"""
        return self.workspace.get_project_from_name(name)
        
    def get_pythonpath(self):
        """Return global PYTHONPATH (for all opened projects"""
        return self.workspace.get_pythonpath()
        
    def add_project(self, folder, silent=False):
        """Add project to tree"""
        if not self.is_valid_project_root_path(folder, silent=silent):
            return
        if not fixpath(folder).startswith(fixpath(self.root_path)):
            title = _("Import directory")
            answer = QMessageBox.warning(self, title,
                            _("The following directory is not in workspace:"
                              "<br><b>%s</b><br><br>"
                              "Do you want to continue (and copy the "
                              "directory to workspace)?") % folder,
                            QMessageBox.Yes|QMessageBox.No)
            if answer == QMessageBox.No:
                return
            name = self._select_project_name(title,
                                             default=osp.basename(folder))
            if name is None:
                return
            dst = self.get_project_path_from_name(name)
            try:
                shutil.copytree(folder, dst)
            except EnvironmentError as error:
                QMessageBox.critical(self, title,
                                     _("<b>Unable to %s <i>%s</i></b>"
                                       "<br><br>Error message:<br>%s"
                                       ) % (_('copy'), folder,
                                            to_text_string(error)))
            folder = dst
        
        project = self.workspace.add_project(folder)
        self.set_folder_names(self.workspace.get_folder_names())
        self.parent_widget.emit(SIGNAL("pythonpath_changed()"))
        
        self.check_for_io_errors()
        
        return project
        
    def open_projects(self, projects, open_related=True):
        """Open projects"""
        self.workspace.open_projects(projects, open_related)
        self.parent_widget.emit(SIGNAL("pythonpath_changed()"))
        self.reset_icon_provider()
        for project in projects:
            self.update(self.get_index(project.root_path))
        
    def close_projects(self, projects):
        """Close projects"""
        self.workspace.close_projects(projects)
        self.parent_widget.emit(SIGNAL("pythonpath_changed()"))
        self.parent_widget.emit(SIGNAL("projects_were_closed()"))
        self.reset_icon_provider()
        for project in projects:
            index = self.get_index(project.root_path)
            self.update(index)
            self.collapse(index)
        
    def remove_projects(self, projects):
        """Remove projects"""
        self.workspace.remove_projects(projects)
        self.set_folder_names(self.workspace.get_folder_names())
        self.parent_widget.emit(SIGNAL("pythonpath_changed()"))
        
    def close_unrelated_projects(self, projects):
        """Close unrelated projects"""
        unrelated_projects = self.workspace.close_unrelated_projects(projects)
        if unrelated_projects:
            self.reset_icon_provider()
            for project in unrelated_projects:
                self.update(self.get_index(project.root_path))
        
    def is_valid_project_root_path(self, root_path, silent=False):
        """Return True root_path is a valid project root path"""
        fixed_wr = fixpath(self.root_path)  # workspace root path
        fixed_pr = fixpath(osp.dirname(root_path))  # project root path
        if self.workspace.has_project(root_path):
            if not silent:
                QMessageBox.critical(self, _("Project Explorer"),
                                     _("The project <b>%s</b>"
                                       " is already opened!"
                                       ) % osp.basename(root_path))
            return False
        elif fixed_pr != fixed_wr and fixed_pr.startswith(fixed_wr):
            if not silent:
                QMessageBox.warning(self, _("Project Explorer"),
                                    _("The project root path directory "
                                      "is inside the workspace but not as the "
                                      "expected tree level. It is not a "
                                      "directory of the workspace:<br>"
                                      "<b>%s</b>") % self.get_workspace())
        return True
    
    def _select_project_name(self, title, default=None):
        """Select project name"""
        name = '' if default is None else default
        while True:
            name, valid = QInputDialog.getText(self, title, _('Project name:'),
                                               QLineEdit.Normal, name)
            if valid and name:
                name = to_text_string(name)
                pattern = r'[a-zA-Z][a-zA-Z0-9\_\-]*$'
                match = re.match(pattern, name)
                path = self.get_project_path_from_name(name)
                if self.workspace.has_project(name):
                    QMessageBox.critical(self, title,
                                         _("A project named "
                                           "<b>%s</b> already exists") % name)
                    continue
                elif match is None:
                    QMessageBox.critical(self, title,
                                         _("Invalid project name.<br><br>"
                                           "Name must match the following "
                                           "regular expression:"
                                           "<br><b>%s</b>") % pattern)
                    continue
                elif osp.isdir(path):
                    answer = QMessageBox.warning(self, title,
                                    _("The following directory is not empty:"
                                      "<br><b>%s</b><br><br>"
                                      "Do you want to continue?") % path,
                                    QMessageBox.Yes|QMessageBox.No)
                    if answer == QMessageBox.No:
                        continue
                return name
            else:
                return
    
    def new_project(self):
        """Return True if project was created"""
        title = _('New project')
        if self.workspace.is_valid():
            name = self._select_project_name(title)
            if name is not None:
                folder = self.get_project_path_from_name(name)
                self.add_project(folder)
        else:
            answer = QMessageBox.critical(self, title,
                                          _("The current workspace has "
                                            "not been configured yet.\n"
                                            "Do you want to do this now?"),
                                          QMessageBox.Yes|QMessageBox.Cancel)
            if answer == QMessageBox.Yes:
                self.emit(SIGNAL('select_workspace()'))
        
    def _select_existing_directory(self):
        """Select existing source code directory,
        to be used as a new project root path
        (copied into the current project's workspace directory if necessary)"""
        if self.last_folder is None:
            self.last_folder = self.workspace.root_path
        while True:
            self.parent_widget.emit(SIGNAL('redirect_stdio(bool)'), False)
            folder = getexistingdirectory(self, _("Select directory"),
                                          self.last_folder)
            self.parent_widget.emit(SIGNAL('redirect_stdio(bool)'), True)
            if folder:
                folder = osp.abspath(folder)
                self.last_folder = folder
                if not self.is_valid_project_root_path(folder):
                    continue
                return folder
            else:
                return
    
    def import_existing_directory(self):
        """Create project from existing directory
        Eventually copy the whole directory to current workspace"""
        folder = self._select_existing_directory()
        if folder is None:
            return
        self.add_project(folder)
    
    def __select_existing_project(self, typename, configname):
        """Select existing project"""
        title = _('Import existing project')
        while True:
            folder = self._select_existing_directory()
            if folder is None:
                return
            if not osp.isfile(osp.join(folder, configname)):
                subfolders = [osp.join(folder, _f) for _f in os.listdir(folder)
                              if osp.isdir(osp.join(folder, _f))
                              and osp.isfile(osp.join(folder, _f, configname))]
                if subfolders:
                    data = []
                    for subfolder in subfolders:
                        data.append((subfolder, False))
                    comment = _("Select projects to import")
                    result = fedit(data, title=title, comment=comment)
                    if result is None:
                        return
                    else:
                        selected_folders = []
                        for index, is_selected in enumerate(result):
                            if is_selected:
                                selected_folders.append(subfolders[index])
                        return selected_folders
                else:
                    QMessageBox.critical(self, title,
                                     _("The folder <i>%s</i> "
                                       "does not contain a valid %s project"
                                       ) % (osp.basename(folder), typename))
                    continue
            return folder
    
    def import_existing_project(self):
        """Import existing project"""
        folders = self.__select_existing_project("Spyder", Project.CONFIG_NAME)
        if folders is None:
            return
        if not isinstance(folders, (tuple, list)):
            folders = [folders]
        for folder in folders:
            self.add_project(folder, silent=True)
    
    def import_existing_pydev_project(self):
        """Import existing Pydev project"""
        folders = self.__select_existing_project("Pydev", ".pydevproject")
        if folders is None:
            return
        if not isinstance(folders, (tuple, list)):
            folders = [folders]
        for folder in folders:
            try:
                name, related_projects, path = get_pydev_project_infos(folder)
            except RuntimeError as error:
                QMessageBox.critical(self,
                            _('Import existing Pydev project'),
                            _("<b>Unable to read Pydev project <i>%s</i></b>"
                              "<br><br>Error message:<br>%s"
                              ) % (osp.basename(folder),
                                   to_text_string(error)))
            finally:
                project = self.add_project(folder, silent=True)
                if project is not None:
                    project.name = name
                    project.set_related_projects(related_projects)
                    project.set_pythonpath(path)
                    self.parent_widget.emit(SIGNAL("pythonpath_changed()"))

    def rename_file(self, fname):
        """Rename file"""
        path = FilteredDirView.rename_file(self, fname)
        if path:
            project = self.get_source_project(fname)
            if project.is_root_path(fname):
                self.workspace.rename_project(project, osp.basename(path))
                self.set_folder_names(self.workspace.get_folder_names())
            else:
                self.remove_path_from_project_pythonpath(project, fname)
    
    def remove_tree(self, dirname):
        """Remove whole directory tree"""
        FilteredDirView.remove_tree(self, dirname)
        project = self.get_source_project(dirname)
        self.remove_path_from_project_pythonpath(project, dirname)
    
    def delete_file(self, fname, multiple, yes_to_all):
        """Delete file"""
        if multiple:
            pj_buttons = QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel
        else:
            pj_buttons = QMessageBox.Yes|QMessageBox.No
        project = self.get_source_project(fname)
        if project.is_root_path(fname):
            answer = QMessageBox.warning(self, _("Delete"),
                            _("Do you really want "
                              "to delete project <b>%s</b>?<br><br>"
                              "Note: project files won't be deleted from "
                              "disk.") % project.name, pj_buttons)
            if answer == QMessageBox.Yes:
                self.remove_projects([project])
                return yes_to_all
        else:
            return FilteredDirView.delete_file(self, fname, multiple,
                                               yes_to_all)
    
    def add_to_path(self, fnames):
        """Add fnames to path"""
        indexes = []
        for path in fnames:
            project = self.get_source_project(path)
            if project.add_to_pythonpath(path):
                self.parent_widget.emit(SIGNAL("pythonpath_changed()"))
                indexes.append(self.get_index(path))
        if indexes:
            self.reset_icon_provider()
            for index in indexes:
                self.update(index)
    
    def remove_path_from_project_pythonpath(self, project, path):
        """Remove path from project's PYTHONPATH"""
        ok = project.remove_from_pythonpath(path)
        self.parent_widget.emit(SIGNAL("pythonpath_changed()"))
        return ok
    
    def remove_from_path(self, fnames):
        """Remove from path"""
        indexes = []
        for path in fnames:
            project = self.get_source_project(path)
            if self.remove_path_from_project_pythonpath(project, path):
                indexes.append(self.get_index(path))
        if indexes:
            self.reset_icon_provider()
            for index in indexes:
                self.update(index)
    
    def manage_path(self, projects):
        """Manage path"""
        for project in projects:
            pathlist = project.get_pythonpath()
            dlg = PathManager(self, pathlist, sync=False)
            dlg.exec_()
            project.set_pythonpath(dlg.get_path_list())
            self.parent_widget.emit(SIGNAL("pythonpath_changed()"))
    
    def edit_related_projects(self, projects):
        """Edit related projects"""
        title = _('Related projects')
        for project in projects:
            related_projects = project.get_related_projects()
            data = []
            other_projects = self.workspace.get_other_projects(project)
            for proj in other_projects:
                name = proj.name
                data.append((name, name in related_projects))
            comment = _("Select projects which are related to "
                        "<b>%s</b>") % project.name
            result = fedit(data, title=title, comment=comment)
            if result is not None:
                related_projects = []
                for index, is_related in enumerate(result):
                    if is_related:
                        name = other_projects[index].name
                        related_projects.append(name)
                project.set_related_projects(related_projects)
    
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
                                  "(Python, C/C++, Fortran)<br><br>"
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
                    self.parent_widget.emit(SIGNAL("removed(QString)"), src)
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


class WorkspaceSelector(QWidget):
    """Workspace selector widget"""
    TITLE = _('Select an existing workspace directory, or create a new one')
    TIP = _("<u><b>What is the workspace?</b></u>"
            "<br><br>"
            "A <b>Spyder workspace</b> is a directory on your filesystem that "
            "contains Spyder projects and <b>.spyderworkspace</b> configuration "
            "file."
            "<br><br>"
            "A <b>Spyder project</b> is a directory with source code (and other "
            "related files) and a configuration file (named "
            "<b>.spyderproject</b>) with project settings (PYTHONPATH, linked "
            "projects, ...).<br>"
            )

    def __init__(self, parent):
        super(WorkspaceSelector, self).__init__(parent)
        self.browse_btn = None
        self.create_btn = None
        self.line_edit = None
        self.first_time = True
        
    def set_workspace(self, path):
        """Set workspace directory"""
        self.line_edit.setText(path)
        
    def setup_widget(self):
        """Setup workspace selector widget"""
        self.line_edit = QLineEdit()
        self.line_edit.setAlignment(Qt.AlignRight)
        self.line_edit.setToolTip(_("This is the current workspace directory")\
                                  +'<br><br>'+self.TIP)
        self.line_edit.setReadOnly(True)
        self.line_edit.setDisabled(True)
        self.browse_btn = QPushButton(get_std_icon('DirOpenIcon'), "", self)
        self.browse_btn.setToolTip(self.TITLE)
        self.connect(self.browse_btn, SIGNAL("clicked()"),
                     self.select_directory)
        layout = QHBoxLayout()
        layout.addWidget(self.line_edit)
        layout.addWidget(self.browse_btn)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
    
    def select_directory(self):
        """Select directory"""
        if self.first_time:
            QMessageBox.information(self, self.TITLE, self.TIP)
            self.first_time = False
        basedir = to_text_string(self.line_edit.text())
        if not osp.isdir(basedir):
            basedir = getcwd()
        while True:
            self.parent().emit(SIGNAL('redirect_stdio(bool)'), False)
            directory = getexistingdirectory(self, self.TITLE, basedir)
            self.parent().emit(SIGNAL('redirect_stdio(bool)'), True)
            if not directory:
                break
            path = osp.join(directory, Workspace.CONFIG_NAME)
            if not osp.isfile(path):
                answer = QMessageBox.warning(self, self.TITLE,
                              _("The following directory is not a Spyder "
                                "workspace:<br>%s<br><br>Do you want to "
                                "create a new workspace in this directory?"
                                ) % directory, QMessageBox.Yes|QMessageBox.No)
                if answer == QMessageBox.No:
                    continue
            directory = osp.abspath(osp.normpath(directory))
            self.set_workspace(directory)
            self.emit(SIGNAL('selected_workspace(QString)'), directory)
            break


class ProjectExplorerWidget(QWidget):
    """
    Project Explorer
    
    Signals:
        sig_open_file
        SIGNAL("create_module(QString)")
        SIGNAL("pythonpath_changed()")
        SIGNAL("renamed(QString,QString)")
        SIGNAL("removed(QString)")
    """
    sig_option_changed = Signal(str, object)
    sig_open_file = Signal(str)
    
    def __init__(self, parent, name_filters=['*.py', '*.pyw'],
                 show_all=False, show_hscrollbar=True):
        QWidget.__init__(self, parent)
        self.treewidget = None
        self.selector = None
        self.setup_layout(name_filters, show_all, show_hscrollbar)
        
    def setup_layout(self, name_filters, show_all, show_hscrollbar):
        """Setup project explorer widget layout"""
        self.selector = WorkspaceSelector(self)
        self.selector.setup_widget()
        self.connect(self.selector, SIGNAL('selected_workspace(QString)'),
                     self.set_workspace)

        self.treewidget = ExplorerTreeWidget(self,
                                             show_hscrollbar=show_hscrollbar)
        self.treewidget.setup(name_filters=name_filters, show_all=show_all)
        self.connect(self.treewidget, SIGNAL('select_workspace()'),
                     self.selector.select_directory)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.selector)
        layout.addWidget(self.treewidget)
        self.setLayout(layout)
        
    def set_workspace(self, path):
        """Set current workspace"""
        path = osp.normpath(to_text_string(path))
        if path is not None and osp.isdir(path):
            self.treewidget.set_workspace(path)
            self.selector.set_workspace(path)
    
    def check_for_io_errors(self):
        """Check for I/O errors that may occured when loading/saving 
        projects or the workspace itself and warn the user"""
        self.treewidget.check_for_io_errors()
            
    def get_workspace(self):
        """Return current workspace path"""
        return self.treewidget.get_workspace()
        
    def closing_widget(self):
        """Perform actions before widget is closed"""
        pass
        
    def add_project(self, project):
        """Add project"""
        return self.treewidget.add_project(project)

    def get_pythonpath(self):
        """Return PYTHONPATH"""
        return self.treewidget.get_pythonpath()
    
    def get_source_project(self, fname):
        """Return project which contains source *fname*"""
        return self.treewidget.get_source_project(fname)


class Test(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        vlayout = QVBoxLayout()
        self.setLayout(vlayout)
        
        self.explorer = ProjectExplorerWidget(None, show_all=True)
        self.explorer.set_workspace(r'D:/Python')
#        p1 = self.explorer.add_project(r"D:/Python/spyder")
#        p1.set_pythonpath([r"D:\Python\spyder\spyderlib"])
#        p1.save()
#        self.treewidget.close_projects(p1)
#        _p2 = self.explorer.add_project(r"D:\Python\test_project")
        
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


if __name__ == "__main__":
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    test = Test()
    test.resize(640, 480)
    test.show()
    app.exec_()

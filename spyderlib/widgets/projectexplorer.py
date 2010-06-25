# -*- coding: utf-8 -*-
#
# Copyright © 2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Project Explorer"""

from PyQt4.QtGui import (QDialog, QVBoxLayout, QLabel, QHBoxLayout, QMenu,
                         QWidget, QTreeWidgetItem, QFileIconProvider,
                         QMessageBox, QInputDialog, QLineEdit, QFileDialog)
from PyQt4.QtCore import (Qt, SIGNAL, QFileInfo, QFileSystemWatcher,
                          QUrl)

import os, sys, re, shutil, cPickle
import os.path as osp

# For debugging purpose:
STDOUT = sys.stdout
STDERR = sys.stderr

# Local imports
from spyderlib.utils import (count_lines, rename_file, remove_file, move_file,
                             programs)
from spyderlib.utils.qthelpers import (get_std_icon, translate, create_action,
                                       create_toolbutton, add_actions,
                                       set_item_user_text)
from spyderlib.utils.qthelpers import get_item_user_text as get_item_path
from spyderlib.config import get_icon, get_image_path
from spyderlib.widgets import OneColumnTree
from spyderlib.widgets.formlayout import fedit
from spyderlib.widgets.pathmanager import PathManager


def listdir(path, include='.', exclude=r'\.pyc$|^\.', show_all=False,
            folders_only=False):
    """List files and directories"""
    namelist = []
    dirlist = []
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

def has_children_files(path, include, exclude, show_all):
    try:
        return len( listdir(path, include, exclude, show_all) ) > 0
    except (IOError, OSError):
        return False

def has_subdirectories(path, include, exclude, show_all):
    try:
        return len( listdir(path, include, exclude,
                            show_all, folders_only=True) ) > 0
    except (IOError, OSError):
        return False
    
def is_drive_path(path):
    path = osp.abspath(path)
    return osp.normpath(osp.join(path, osp.pardir)) == path

def get_dir_icon(dirname, expanded=False, pythonpath=False, root=False):
    """Return appropriate directory icon"""
    if is_drive_path(dirname):
        return get_std_icon('DriveHDIcon')
    prefix = 'pp_' if pythonpath else ''
    if root:
        if expanded:
            return get_icon(prefix+'project_expanded.png')
        else:
            return get_icon(prefix+'project_collapsed.png')
    elif osp.isfile(osp.join(dirname, '__init__.py')):
        if expanded:
            return get_icon(prefix+'package_expanded.png')
        else:
            return get_icon(prefix+'package_collapsed.png')
    else:
        if expanded:
            return get_icon(prefix+'folder_expanded.png')
        else:
            return get_icon(prefix+'folder_collapsed.png')
            

class Project(object):
    """Spyder project"""
    CONFIG_NAME = '.spyderproject'
    CONFIG_ATTR = ('name', 'related_projects', 'relative_pythonpath', 'opened')
    def __init__(self, root_path):
        self.name = osp.basename(root_path)
        self.related_projects = [] # storing project path, not project objects
        self.root_path = unicode(root_path)
        self.items = {}
        self.icon_provider = QFileIconProvider()
        self.namesets = {}
        self.pythonpath = []
        self.folders = set()
        self.opened = True

        config_path = self.__get_project_config_path()
        if not osp.exists(config_path):
            self.save()
            
    def _get_relative_pythonpath(self):
        # Workaround to replace os.path.relpath (new in Python v2.6):
        offset = len(self.root_path)+len(os.pathsep)
        return [path[offset:] for path in self.pythonpath]

    def _set_relative_pythonpath(self, value):
        self.pythonpath = [osp.abspath(osp.join(self.root_path, path))
                           for path in value]
        
    relative_pythonpath = property(_get_relative_pythonpath,
                                   _set_relative_pythonpath)
        
    def __get_project_config_path(self):
        return osp.join(self.root_path, self.CONFIG_NAME)
        
    def load(self):
        data = cPickle.load(file(self.__get_project_config_path()))
        # Compatibilty with old project explorer file format:
        if 'relative_pythonpath' not in data:
            print >>STDERR, "Warning: converting old configuration file " \
                            "for project '%s'" % data['name']
            self.pythonpath = data['pythonpath']
            data['relative_pythonpath'] = self.relative_pythonpath
        for attr in self.CONFIG_ATTR:
            setattr(self, attr, data[attr])
        self.save()
    
    def save(self):
        data = {}
        for attr in self.CONFIG_ATTR:
            data[attr] = getattr(self, attr)
        cPickle.dump(data, file(self.__get_project_config_path(), 'w'),
                     cPickle.HIGHEST_PROTOCOL)
        
    def delete(self):
        os.remove(self.__get_project_config_path())
        
    def get_name(self):
        return self.name
        
    def set_name(self, name):
        self.name = name
        if self.root_path in self.items:
            self.items[self.root_path].setText(0, self.name)
        self.save()
        
    def get_root_path(self):
        return self.root_path
    
    def get_root_item(self):
        return self.items[self.root_path]
        
    def get_related_projects(self):
        """Return related projects path list"""
        return self.related_projects
    
    def set_related_projects(self, related_projects):
        self.related_projects = related_projects
        self.save()
        
    def get_file_icon(self, filename):
        ext = osp.splitext(filename)[1][1:]
        icon_path = get_image_path(ext+'.png', default=None)
        if icon_path is None:
            return self.icon_provider.icon(QFileInfo(filename))
        else:
            return get_icon(icon_path)
        
    def set_opened(self, opened):
        self.opened = opened
        self.save()
        
    def is_opened(self):
        return self.opened
        
    def get_pythonpath(self):
        return self.pythonpath[:] # return a copy of pythonpath attribute
        
    def __update_pythonpath_icons(self):
        for path, item in self.items.iteritems():
            if osp.isfile(path):
                continue
            if path == self.root_path and not self.is_opened():
                item.setIcon(0, get_icon('project_closed.png'))
            else:
                item.setIcon(0, get_dir_icon(path, expanded=item.isExpanded(),
                                             pythonpath=path in self.pythonpath,
                                             root=self.is_root_item(item)))
    
    def set_pythonpath(self, pythonpath):
        self.pythonpath = pythonpath
        self.__update_pythonpath_icons()
        self.save()
        
    def get_items(self):
        return self.items.values()
        
    def is_item_in_pythonpath(self, item):
        for dirname, item_i in self.items.iteritems():
            if item_i is item:
                return dirname in self.pythonpath
            
    def is_root_item(self, item):
        return item is self.items[self.root_path]
                
    def create_dir_item(self, dirname, parent, preceding,
                        tree, include, exclude, show_all):
        if dirname in self.items:
            item = self.items[dirname]
            is_expanded = item.isExpanded()
        else:
            if preceding is None:
                item = QTreeWidgetItem(parent, QTreeWidgetItem.Type)
            else:
                item = QTreeWidgetItem(parent, preceding, QTreeWidgetItem.Type)
            is_expanded = False
        flags = Qt.ItemIsSelectable|Qt.ItemIsUserCheckable| \
                Qt.ItemIsEnabled|Qt.ItemIsDropEnabled
        is_root = dirname == self.root_path
        if is_root:
            # Root path: Project root item
            item.setText(0, self.name)
            item.setFlags(flags)
        else:
            item.setText(0, osp.basename(dirname))
            item.setFlags(flags|Qt.ItemIsDragEnabled)
        set_item_user_text(item, dirname)
        in_path = dirname in self.pythonpath
        item.setIcon(0, get_dir_icon(dirname, expanded=is_expanded,
                                     pythonpath=in_path, root=is_root))
        if not item.childCount() and has_children_files(dirname, include,
                                                        exclude, show_all):
            item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
            tree.collapseItem(item)
        else:
            item.setChildIndicatorPolicy(\
                                QTreeWidgetItem.DontShowIndicatorWhenChildless)
        self.folders.add(dirname)
        self.items[dirname] = item
        return item
        
    def create_file_item(self, filename, parent, preceding):
        if filename in self.items:
            return self.items[filename]
        displayed_name = osp.basename(filename)
        if preceding is None:
            item = QTreeWidgetItem(parent, QTreeWidgetItem.Type)
        else:
            item = QTreeWidgetItem(parent, preceding, QTreeWidgetItem.Type)
        item.setFlags(Qt.ItemIsSelectable|Qt.ItemIsUserCheckable|
                      Qt.ItemIsEnabled|Qt.ItemIsDragEnabled)
        item.setText(0, displayed_name)
        set_item_user_text(item, filename)
        item.setIcon(0, self.get_file_icon(filename))
        self.items[filename] = item
        return item
        
    def refresh(self, tree, include, exclude, show_all):
        root_item = self.items[self.root_path]
        if self.is_opened():
            if root_item.childCount():
                root_item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
            icon = get_dir_icon(self.root_path, expanded=root_item.isExpanded(),
                                pythonpath=self.root_path in self.pythonpath,
                                root=True)
            root_item.setIcon(0, icon)
            
            self.clean_items(tree)
            for dirname in self.folders.copy():
                branch = self.items.get(dirname)
                if branch is None or not osp.isdir(dirname):
                    self.folders.remove(dirname)
                    if branch in self.namesets:
                        self.namesets.pop(branch)
                    if dirname in self.items:
                        self.items.pop(dirname)
                    continue
                self.populate_tree(tree, include, exclude,
                                   show_all, branch=branch)
        else:
            tree.collapseItem(root_item)
            root_item.setChildIndicatorPolicy(QTreeWidgetItem.DontShowIndicator)
            root_item.setIcon(0, get_icon('project_closed.png'))
            tree.remove_from_watcher(self)
        
    def get_monitored_pathlist(self):
        pathlist = [self.root_path]
        for branch in self.namesets.keys():
            if isinstance(branch, QTreeWidgetItem) and branch in self.items:
                pathlist.append(get_item_path(branch))
        return pathlist
        
    def remove_from_tree(self, tree):
        tree.remove_from_watcher(self)
        root_item = self.items[self.root_path]
        tree.takeTopLevelItem(tree.indexOfTopLevelItem(root_item))
        
    def clean_items(self, tree):
        """
        Clean items dictionary following drag'n drop operation:
        unfortunately, QTreeWidget does not emit any signal following an 
        item deletion
        """
        for name, item in self.items.items():
            try:
                item.text(0)
            except RuntimeError:
                self.items.pop(name)
                if name in self.folders:
                    self.folders.remove(name)
                if name in self.namesets:
                    self.namesets.pop(name)
        
    def populate_tree(self, tree, include, exclude, show_all, branch=None):
        dirnames, filenames = [], []
        if branch is None or branch is tree:
            branch = tree
            branch_path = self.root_path
        else:
            branch_path = get_item_path(branch)
        for path in listdir(branch_path, include, exclude, show_all):
            abspath = osp.abspath(osp.join(branch_path, path))
            if osp.isdir(abspath):
                dirnames.append(abspath)
            else:
                filenames.append(abspath)
        # Populating tree: directories
        if branch is tree:
            dirs = {branch_path:
                    self.create_dir_item(branch_path, tree, None,
                                         tree, include, exclude, show_all)}
        else:
            dirs = {branch_path: branch}
        item_preceding = None
        for dirname in sorted(dirnames):
            parent_dirname = abspardir(dirname)
            parent = dirs.get(parent_dirname)
            if parent is None and parent_dirname != branch_path:
                # This is related to directories which contain single
                # nested subdirectories
                items_to_create = []
                while dirs.get(parent_dirname) is None:
                    items_to_create.append(parent_dirname)
                    parent_dirname = abspardir(parent_dirname)
                items_to_create.reverse()
                for item_dir in items_to_create:
                    item_parent = dirs[abspardir(item_dir)]
                    dirs[item_dir] = self.create_dir_item(item_dir, item_parent,
                            item_preceding, tree, include, exclude, show_all)
                parent_dirname = abspardir(dirname)
                parent = dirs[parent_dirname]
            if item_preceding is None:
                item_preceding = parent
            item_preceding = self.create_dir_item(dirname, parent,
                                                  item_preceding, tree,
                                                  include, exclude, show_all)
            dirs[dirname] = item_preceding
        # Populating tree: files
        for filename in sorted(filenames):
            parent_item = dirs[osp.dirname(filename)]
            item_preceding = self.create_file_item(filename, parent_item,
                                                   item_preceding)
        # Removed files and directories
        old_set = self.namesets.get(branch)
        new_set = set(filenames+dirnames+[branch_path])
        self.namesets[branch] = new_set
        tree.add_to_watcher(self)
        if old_set is not None:
            for name in old_set-new_set:
                # If name is not in self.items, that is because method
                # 'clean_items' has already removed it
                if name in self.items:
                    item = self.items.pop(name)
    #                try:
                    item.parent().removeChild(item)
    #                except RuntimeError:
    #                    # Item has already been deleted by PyQt
    #                    pass


def get_pydev_project_infos(project_path):
    """Return Pydev project infos: name, related projects and PYTHONPATH"""
    import xml.etree.ElementTree as ElementTree
    
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


class ExplorerTreeWidget(OneColumnTree):
    """
    ExplorerTreeWidget
    """
    def __init__(self, parent):
        OneColumnTree.__init__(self, parent)
        self.parent_widget = parent
        
        self.projects = []
        self.__update_title()
        
        self.watcher = QFileSystemWatcher(self)
        self.watcher_pathlist = []
        self.connect(self.watcher, SIGNAL("directoryChanged(QString)"),
                     self.directory_changed)
        self.connect(self.watcher, SIGNAL("fileChanged(QString)"),
                     self.file_changed)

        self.include = None
        self.exclude = None
        self.show_all = None
        self.valid_types = None

        self.last_folder = ""
        
        self.connect(self, SIGNAL('itemExpanded(QTreeWidgetItem*)'),
                     self.item_expanded)
        self.connect(self, SIGNAL('itemCollapsed(QTreeWidgetItem*)'),
                     self.item_collapsed)
        
        self.setSelectionMode(OneColumnTree.ExtendedSelection)
        
        # Enable drag & drop events
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setAutoExpandDelay(500)
        
    def get_project_from_name(self, name):
        for project in self.projects:
            if project.get_name() == name:
                return project
        
    def get_pythonpath(self):
        pythonpath = []
        for project in self.projects:
            if project.is_opened():
                pythonpath += project.get_pythonpath()
        return pythonpath
        
    def setup(self, include='.', exclude=r'\.pyc$|^\.', show_all=False,
              valid_types=['.py', '.pyw']):
        self.include = include
        self.exclude = exclude
        self.show_all = show_all
        self.valid_types = valid_types
        
    def __get_project_from_item(self, item):
        for project in self.projects:
            if item in project.get_items():
                return project
        
    def get_actions_from_items(self, items):
        """Reimplemented OneColumnTree method"""
        if items:
            pjitems = [(self.__get_project_from_item(_it), _it)
                       for _it in items]
            projects = [_proj for _proj, _it in pjitems]
            are_root_items = [_proj.is_root_item(_it) for _proj, _it in pjitems]
            any_project = any(are_root_items)
            are_folder_items = [osp.isdir(get_item_path(_it)) for _it in items]
            only_folders = all(are_folder_items)
            any_folder_in_path = any([_proj.is_item_in_pythonpath(_it)
                                      for _proj, _it in pjitems])
            any_folder_not_in_path = only_folders and \
                                     any([not _proj.is_item_in_pythonpath(_it)
                                          for _proj, _it in pjitems])

        actions = []

        if items and not only_folders:
            open_file_act = create_action(self,
                              text=translate('ProjectExplorer', 'Open'),
                              triggered=lambda: self.open_file_from_menu(items))
            actions.append(open_file_act)
        
        new_project_act = create_action(self,
                            text=translate('ProjectExplorer', 'Project...'),
                            icon=get_icon('project_expanded.png'),
                            triggered=self.new_project)
        if items:
            new_file_act = create_action(self,
                                text=translate('ProjectExplorer', 'File...'),
                                icon=get_icon('filenew.png'),
                                triggered=lambda: self.new_file(items[-1]))
            new_folder_act = create_action(self,
                                text=translate('ProjectExplorer', 'Folder...'),
                                icon=get_icon('folder_collapsed.png'),
                                triggered=lambda: self.new_folder(items[-1]))
            new_module_act = create_action(self,
                                text=translate('ProjectExplorer', 'Module...'),
                                icon=get_icon('py.png'),
                                triggered=lambda: self.new_module(items[-1]))
            new_package_act = create_action(self,
                                icon=get_icon('package_collapsed.png'),
                                text=translate('ProjectExplorer', 'Package...'),
                                triggered=lambda: self.new_package(items[-1]))
            new_act_menu = QMenu(translate('ProjectExplorer', 'New'), self)
            add_actions(new_act_menu, (new_project_act, None,
                                       new_file_act, new_folder_act, None,
                                       new_module_act, new_package_act))
            actions.append(new_act_menu)
        else:
            new_project_act.setText(translate('ProjectExplorer',
                                              'New project...'))
            actions.append(new_project_act)
        
        import_spyder_act = create_action(self,
                            text=translate('ProjectExplorer',
                                           'Existing Spyder project'),
                            icon=get_icon('spyder.svg'),
                            triggered=self.import_existing_project)
        import_pydev_act = create_action(self,
                            text=translate('ProjectExplorer',
                                           'Existing Pydev project'),
                            icon=get_icon('pydev.png'),
                            triggered=self.import_existing_pydev_project)
        import_act_menu = QMenu(translate('ProjectExplorer', 'Import'), self)
        add_actions(import_act_menu, (import_spyder_act, import_pydev_act))
        actions += [import_act_menu, None]
        
        if not items:
            return actions
            
        open_act = create_action(self,
                            text=translate('ProjectExplorer', 'Open project'),
                            icon=get_icon('project_expanded.png'),
                            triggered=lambda: self.open_project(projects))
        close_act = create_action(self,
                            text=translate('ProjectExplorer', 'Close project'),
                            icon=get_icon('project_closed.png'),
                            triggered=lambda: self.close_project(projects))
        close_unrelated_act = create_action(self,
                text=translate('ProjectExplorer', 'Close unrelated projects'),
                triggered=lambda: self.close_unrelated_projects(projects))
        manage_path_act = create_action(self, icon=get_icon('pythonpath.png'),
                            text=translate('ProjectExplorer',
                                           'PYTHONPATH manager'),
                            triggered=lambda: self.manage_path(projects))
        relproj_act = create_action(self,
                    text=translate('ProjectExplorer', 'Edit related projects'),
                    triggered=lambda: self.edit_related_projects(projects))
        relproj_act.setEnabled(len(self.projects) > 1)
        if any_project:
            if any([not _proj.is_opened() for _proj in projects]):
                actions += [open_act]
            if any([_proj.is_opened() for _proj in projects]):
                actions += [close_act, close_unrelated_act]
            actions += [manage_path_act, relproj_act, None]
                
        rename_act = create_action(self,
                            text=translate('ProjectExplorer', 'Rename...'),
                            icon=get_icon('rename.png'),
                            triggered=lambda: self.rename(items))
        delete_act = create_action(self,
                            text=translate('ProjectExplorer', 'Delete'),
                            icon=get_icon('delete.png'),
                            triggered=lambda: self.delete(items))
        actions += [rename_act, delete_act, None]
        
        add_to_path_act = create_action(self,
                            text=translate('ProjectExplorer',
                                           'Add to PYTHONPATH'),
                            icon=get_icon('add_to_path.png'),
                            triggered=lambda: self.add_to_path(items))
        remove_from_path_act = create_action(self,
                            text=translate('ProjectExplorer',
                                           'Remove from PYTHONPATH'),
                            icon=get_icon('remove_from_path.png'),
                            triggered=lambda: self.remove_from_path(items))
        properties_act = create_action(self,
                            text=translate('ProjectExplorer', 'Properties'),
                            icon=get_icon('advanced.png'),
                            triggered=lambda: self.show_properties(items))
        
        if os.name == 'nt':
            winexp_act = create_action(self,
                            text=translate('ProjectExplorer',
                                           "Open in Windows Explorer"),
                            icon="magnifier.png",
                            triggered=lambda: self.open_windows_explorer(items))
            _title = translate('ProjectExplorer', "Open command prompt here")
        else:
            winexp_act = None
            _title = translate('ProjectExplorer', "Open terminal here")
        terminal_act = create_action(self, text=_title, icon="cmdprompt.png",
                            triggered=lambda: self.open_terminal(items))
        _title = translate('ProjectExplorer', "Open Python interpreter here")
        interpreter_act = create_action(self, text=_title, icon="python.png",
                            triggered=lambda: self.open_interpreter(items))
        
        if only_folders:
            if any_folder_not_in_path:
                actions += [add_to_path_act]
            if any_folder_in_path:
                actions += [remove_from_path_act]
            actions += [None, winexp_act, terminal_act, interpreter_act]
            if programs.is_module_installed("IPython"):
                ipython_act = create_action(self,
                        text=translate('ProjectExplorer', "Open IPython here"),
                        icon="ipython.png",
                        triggered=lambda: self.open_ipython(items))
                actions.append(ipython_act)
        actions += [None, properties_act]
        
        return actions
        
    def add_to_watcher(self, project):
        for path in project.get_monitored_pathlist():
            if path in self.watcher_pathlist:
                continue
            self.watcher.addPath(path)
            self.watcher_pathlist.append(path)
            
    def remove_from_watcher(self, project):
        for path in project.get_monitored_pathlist():
            if path not in self.watcher_pathlist:
                continue
            self.watcher.removePath(path)
            self.watcher_pathlist.pop(self.watcher_pathlist.index(path))
        
    def directory_changed(self, qstr):
        path = osp.abspath(unicode(qstr))
        for project in self.projects:
            if path in project.folders:
                project.refresh(self, self.include, self.exclude, self.show_all)
        
    def file_changed(self, qstr):
        self.directory_changed(osp.dirname(unicode(qstr)))

    def is_item_expandable(self, item):
        """Reimplemented OneColumnTree method"""
        return item.childIndicatorPolicy() == QTreeWidgetItem.ShowIndicator \
               and not item.isExpanded()
        
    def expandAll(self):
        """Reimplement QTreeWidget method"""
        self.clearSelection()
        for item in self.get_top_level_items():
            item.setSelected(True)
        self.expand_selection()
        self.clearSelection()
        
    def keyPressEvent(self, event):
        """Reimplement Qt method"""
        if event.key() == Qt.Key_F2:
            self.rename(self.currentItem())
            event.accept()
        else:
            super(ExplorerTreeWidget, self).keyPressEvent(event)

    def activated(self):
        """Reimplement OneColumnTree method"""
        path = get_item_path(self.currentItem())
        if path is not None and osp.isfile(path):
            self.open_file(path)
            
    def open_file(self, fname):
        ext = osp.splitext(fname)[1]
        if ext in self.valid_types:
            self.parent_widget.emit(SIGNAL("open_file(QString)"), fname)
        else:
            self.startfile(fname)
        
    def startfile(self, fname=None):
        """Windows only: open file in the associated application"""
        if fname is None:
            fname = self.get_filename()
        emit = False
        if os.name == 'nt':
            try:
                os.startfile(fname)
            except WindowsError:
                emit = True
        else:
            emit = True
        if emit:
            self.parent_widget.emit(SIGNAL("edit(QString)"), fname)
                
    def item_expanded(self, item):
        project = self.__get_project_from_item(item)
        if osp.isfile(get_item_path(item)):
            return
        in_path = project.is_item_in_pythonpath(item)
        is_root = project.is_root_item(item)
        if project.is_opened():
            icon = get_dir_icon(get_item_path(item), expanded=True,
                                pythonpath=in_path, root=is_root)
        else:
            icon = get_icon('project_closed.png')
        item.setIcon(0, icon)
        if not item.childCount():
            # A non-populated item was just expanded
            for project in self.projects:
                if item in project.get_items():
                    project.populate_tree(self, self.include, self.exclude,
                                          self.show_all, branch=item)
                    self.scrollToItem(item)
            
    def item_collapsed(self, item):
        project = self.__get_project_from_item(item)
        in_path = project.is_item_in_pythonpath(item)
        is_root = project.is_root_item(item)
        if project.is_opened():
            icon = get_dir_icon(get_item_path(item), expanded=False,
                                pythonpath=in_path, root=is_root)
        else:
            icon = get_icon('project_closed.png')
        item.setIcon(0, icon)
        
    def __update_title(self):
        nb = len(self.projects)
        title = unicode("%d "+translate('ProjectExplorer', 'project')) % nb
        if nb > 1:
            title += "s"
        self.set_title(title)
        
    def __sort_toplevel_items(self):
        self.sort_top_level_items(key=lambda item: item.text(0).toLower())
        
    def add_project(self, root_path, silent=False):
        if self.is_project_already_here(root_path, silent=silent):
            return
        project = Project(root_path)
        project.load()
        self.projects.append(project)
        self.__update_title()
        self.save_expanded_state()
        project.populate_tree(self, self.include, self.exclude, self.show_all)
        project.refresh(self, self.include, self.exclude, self.show_all)
        self.restore_expanded_state()
        self.__sort_toplevel_items()
        self.parent_widget.emit(SIGNAL("pythonpath_changed()"))
        return project
        
    def open_project(self, projects, open_related=True):
        if not isinstance(projects, (tuple, list)):
            projects = [projects]
        for project in projects:
            project.set_opened(True)
            project.refresh(self, self.include, self.exclude, self.show_all)
            related_projects = project.get_related_projects()
            if open_related:
                for projname in related_projects:
                    for relproj in self.projects:
                        if relproj.get_name() == projname:
                            self.open_project(relproj, open_related=False)
        self.parent_widget.emit(SIGNAL("pythonpath_changed()"))
        
    def close_project(self, projects):
        if not isinstance(projects, (tuple, list)):
            projects = [projects]
        for project in projects:
            project.set_opened(False)
            project.refresh(self, self.include, self.exclude, self.show_all)
        self.parent_widget.emit(SIGNAL("pythonpath_changed()"))
        
    def remove_project(self, projects):
        if not isinstance(projects, (tuple, list)):
            projects = [projects]
        for project in projects:
            project.remove_from_tree(self)
            project.delete()
            self.projects.pop(self.projects.index(project))
            self.__update_title()
            self.parent_widget.emit(SIGNAL("pythonpath_changed()"))
        
    def close_unrelated_projects(self, projects):
        if not isinstance(projects, (tuple, list)):
            projects = [projects]
        unrelated_projects = []
        for project in projects:
            for proj in self.projects:
                if proj is project:
                    continue
                if proj.get_name() in project.get_related_projects():
                    continue
                if project.get_name() in proj.get_related_projects():
                    continue
                unrelated_projects.append(proj)
        self.close_project(unrelated_projects)
        
    def __set_last_folder(self):
        if self.last_folder:
            return
        opened_projects = [_p for _p in self.projects if _p.is_opened()]
        if opened_projects:
            root_path = opened_projects[0].root_path
        elif self.projects:
            root_path = self.projects[0].root_path
        else:
            return
        self.last_folder = osp.join(root_path, osp.pardir)
        
    def is_project_already_here(self, root_path, silent=False):
        if root_path in [project.root_path for project in self.projects]:
            if not silent:
                QMessageBox.critical(self,
                        translate('ProjectExplorer', "Project Explorer"),
                        translate('ProjectExplorer', "The project <b>%1</b>"
                                  " is already opened!"
                                  ).arg(osp.basename(root_path)))
            return True
        else:
            return False
        
    def __select_project_root_path(self):
        self.__set_last_folder()
        while True:
            self.parent_widget.emit(SIGNAL('redirect_stdio(bool)'), False)
            folder = QFileDialog.getExistingDirectory(self,
                      translate('ProjectExplorer', "Select project root path"),
                      self.last_folder)
            self.parent_widget.emit(SIGNAL('redirect_stdio(bool)'), True)
            if folder.isEmpty():
                return
            else:
                folder = osp.abspath(unicode(folder))
                self.last_folder = folder
                if self.is_project_already_here(folder):
                    continue
                return folder
        
    def new_project(self):
        """Return True if project was created"""
        folder = self.__select_project_root_path()
        if folder is None:
            return
        title = translate('ProjectExplorer', 'New project')
        name = osp.basename(folder)
        while True:
            name, valid = QInputDialog.getText(self, title,
                               translate('ProjectExplorer', 'Project name:'),
                               QLineEdit.Normal, name)
            if valid and name:
                name = unicode(name)
                if name in [project.name for project in self.projects]:
                    QMessageBox.critical(self, title,
                            translate('ProjectExplorer', "A project named "
                                      "<b>%1</b> already exists").arg(name))
                    continue
                project = self.add_project(folder)
                project.set_name(name)
                return True
    
    def __select_existing_project(self, typename, configname):
        title = translate('ProjectExplorer', 'Import existing project')
        while True:
            folder = self.__select_project_root_path()
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
                    comment = translate('ProjectExplorer',
                                        "Select projects to import")
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
                         translate('ProjectExplorer', "The folder <i>%1</i> "
                                   "does not contain a valid %2 project"
                                   ).arg(osp.basename(folder)).arg(typename))
                    continue
            return folder
    
    def import_existing_project(self):
        folders = self.__select_existing_project("Spyder", Project.CONFIG_NAME)
        if folders is None:
            return
        if not isinstance(folders, (tuple, list)):
            folders = [folders]
        for folder in folders:
            self.add_project(folder, silent=True)
    
    def import_existing_pydev_project(self):
        folders = self.__select_existing_project("Pydev", ".pydevproject")
        if folders is None:
            return
        if not isinstance(folders, (tuple, list)):
            folders = [folders]
        for folder in folders:
            try:
                name, related_projects, path = get_pydev_project_infos(folder)
            except RuntimeError, error:
                QMessageBox.critical(self,
                    translate('ProjectExplorer', 'Import existing Pydev project'),
                    translate('ProjectExplorer',
                              "<b>Unable to read Pydev project <i>%1</i></b>"
                              "<br><br>Error message:<br>%2") \
                    .arg(osp.basename(folder)).arg(str(error)))
            finally:
                project = self.add_project(folder, silent=True)
                if project is not None:
                    project.set_name(name)
                    project.set_related_projects(related_projects)
                    project.set_pythonpath(path)
                    self.parent_widget.emit(SIGNAL("pythonpath_changed()"))
    
    def __create_new_file(self, item, title, filters, create_func):
        current_path = get_item_path(item)
        if osp.isfile(current_path):
            current_path = osp.dirname(current_path)
        self.parent_widget.emit(SIGNAL('redirect_stdio(bool)'), False)
        fname = QFileDialog.getSaveFileName(self, title, current_path, filters)
        self.parent_widget.emit(SIGNAL('redirect_stdio(bool)'), True)
        if fname:
            try:
                create_func(unicode(fname))
            except EnvironmentError, error:
                QMessageBox.critical(self,
                                 translate('ProjectExplorer', "New file"),
                                 translate('ProjectExplorer',
                                           "<b>Unable to create file <i>%1</i>"
                                           "</b><br><br>Error message:<br>%2"
                                           ).arg(fname).arg(str(error)))
            finally:
                self.parent_widget.emit(SIGNAL("edit(QString)"), fname)
    
    def new_file(self, item):
        title = translate('ProjectExplorer', "New file")
        filters = translate('Explorer', "All files")+" (*.*)"
        create_func = lambda fname: file(fname, 'wb').write('')
        self.__create_new_file(item, title, filters, create_func)
    
    def __create_new_folder(self, item, title, subtitle, is_package):
        current_path = get_item_path(item)
        if osp.isfile(current_path):
            current_path = osp.dirname(current_path)
        name, valid = QInputDialog.getText(self, title, subtitle,
                                           QLineEdit.Normal, "")
        if valid:
            dirname = osp.join(current_path, unicode(name))
            try:
                os.mkdir(dirname)
            except EnvironmentError, error:
                QMessageBox.critical(self, title,
                                     translate('ProjectExplorer', "<b>Unable "
                                               "to create folder <i>%1</i></b>"
                                               "<br><br>Error message:<br>%2"
                                               ).arg(dirname).arg(str(error)))
            finally:
                if is_package:
                    fname = osp.join(dirname, '__init__.py')
                    try:
                        file(fname, 'wb').write('#')
                    except EnvironmentError, error:
                        QMessageBox.critical(self, title,
                                     translate('ProjectExplorer', "<b>Unable "
                                               "to create file <i>%1</i></b>"
                                               "<br><br>Error message:<br>%2"
                                               ).arg(fname).arg(str(error)))

    def new_folder(self, item):
        title = translate('ProjectExplorer', 'New folder')
        subtitle = translate('ProjectExplorer', 'Folder name:')
        self.__create_new_folder(item, title, subtitle, is_package=False)
    
    def new_module(self, item):
        title = translate('ProjectExplorer', "New module")
        filters = translate('Explorer', "Python scripts")+" (*.py *.pyw)"
        create_func = lambda fname: self.parent_widget.emit( \
                                     SIGNAL("create_module(QString)"), fname)
        self.__create_new_file(item, title, filters, create_func)
    
    def new_package(self, item):
        title = translate('ProjectExplorer', 'New package')
        subtitle = translate('ProjectExplorer', 'Package name:')
        self.__create_new_folder(item, title, subtitle, is_package=True)
    
    def open_file_from_menu(self, items):
        if not isinstance(items, (tuple, list)):
            items = [items]
        for item in items:
            project = self.__get_project_from_item(item)
            if not project.is_root_item(item):
                fname = get_item_path(item)
                if osp.isfile(fname):
                    self.open_file(fname)
    
    def rename(self, items):
        if not isinstance(items, (tuple, list)):
            items = [items]
        for item in items:
            project = self.__get_project_from_item(item)
            if project.is_root_item(item):
                name, valid = QInputDialog.getText(self,
                                      translate('ProjectExplorer', 'Rename'),
                                      translate('ProjectExplorer', 'New name:'),
                                      QLineEdit.Normal, project.name)
                if valid:
                    old_name = project.name
                    new_name = unicode(name)
                    for proj in self.projects:
                        relproj = proj.get_related_projects()
                        if old_name in relproj:
                            relproj[relproj.index(old_name)] = new_name
                            proj.set_related_projects(relproj)
                    project.set_name(new_name)
                    self.__sort_toplevel_items()
            else:
                fname = get_item_path(item)
                path, valid = QInputDialog.getText(self,
                                      translate('ProjectExplorer', 'Rename'),
                                      translate('ProjectExplorer', 'New name:'),
                                      QLineEdit.Normal, osp.basename(fname))
                if valid:
                    path = osp.join(osp.dirname(fname), unicode(path))
                    if path == fname:
                        continue
                    try:
                        rename_file(fname, path)
                        self.parent_widget.emit( \
                             SIGNAL("renamed(QString,QString)"), fname, path)
                        self.remove_path_from_project_pythonpath(project, fname)
                    except EnvironmentError, error:
                        QMessageBox.critical(self,
                            translate('ProjectExplorer', "Rename"),
                            translate('ProjectExplorer',
                                      "<b>Unable to rename file <i>%1</i></b>"
                                      "<br><br>Error message:<br>%2") \
                            .arg(osp.basename(fname)).arg(str(error)))
                project.refresh(self, self.include, self.exclude, self.show_all)
        
    def delete(self, items):
        # Don't forget to change PYTHONPATH accordingly
        if len(items) > 1:
            buttons = QMessageBox.Yes|QMessageBox.YesAll| \
                      QMessageBox.No|QMessageBox.Cancel
            pj_buttons = QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel
        else:
            buttons = QMessageBox.Yes|QMessageBox.No
            pj_buttons = QMessageBox.Yes|QMessageBox.No
        yes_to_all = None
        for item in items:
            project = self.__get_project_from_item(item)
            if project.is_root_item(item):
                answer = QMessageBox.warning(self,
                        translate("ProjectExplorer", "Delete"),
                        translate("ProjectExplorer", "Do you really want "
                                  "to delete project <b>%1</b>?<br><br>"
                                  "Note: project files won't be deleted from "
                                  "disk.").arg(project.get_name()), pj_buttons)
                if answer == QMessageBox.Yes:
                    self.remove_project(project)
                elif answer == QMessageBox.Cancel:
                    return
            else:
                fname = get_item_path(item)
                if yes_to_all is None:
                    answer = QMessageBox.warning(self,
                            translate("ProjectExplorer", "Delete"),
                            translate("ProjectExplorer", "Do you really want "
                                      "to delete <b>%1</b>?") \
                            .arg(osp.basename(fname)), buttons)
                    if answer == QMessageBox.No:
                        continue
                    elif answer == QMessageBox.Cancel:
                        return
                    elif answer == QMessageBox.YesAll:
                        yes_to_all = True
                try:
                    if osp.isfile(fname):
                        remove_file(fname)
                        self.parent_widget.emit(SIGNAL("removed(QString)"),
                                                fname)
                    else:
                        shutil.rmtree(fname)
                        self.remove_path_from_project_pythonpath(project, fname)
                        self.parent_widget.emit(SIGNAL("removed_tree(QString)"),
                                                fname)
                except EnvironmentError, error:
                    action_str = translate('ProjectExplorer', 'delete')
                    QMessageBox.critical(self,
                        translate('ProjectExplorer', "Project Explorer"),
                        translate('ProjectExplorer',
                                  "<b>Unable to %1 <i>%2</i></b>"
                                  "<br><br>Error message:<br>%3") \
                        .arg(action_str).arg(fname).arg(str(error)))
    
    def add_path_to_project_pythonpath(self, project, path):
        pathlist = project.get_pythonpath()
        if path in pathlist:
            return
        pathlist.insert(0, path)
        project.set_pythonpath(pathlist)
        self.parent_widget.emit(SIGNAL("pythonpath_changed()"))
    
    def add_to_path(self, items):
        if not isinstance(items, (list, tuple)):
            items = [items]
        for item in items:
            project = self.__get_project_from_item(item)
            path = get_item_path(item)
            self.add_path_to_project_pythonpath(project, path)
    
    def remove_path_from_project_pythonpath(self, project, path):
        pathlist = project.get_pythonpath()
        if path not in pathlist:
            return
        pathlist.pop(pathlist.index(path))
        project.set_pythonpath(pathlist)
        self.parent_widget.emit(SIGNAL("pythonpath_changed()"))
    
    def remove_from_path(self, items):
        if not isinstance(items, (list, tuple)):
            items = [items]
        for item in items:
            project = self.__get_project_from_item(item)
            path = get_item_path(item)
            self.remove_path_from_project_pythonpath(project, path)
    
    def manage_path(self, projects):
        for project in projects:
            pathlist = project.get_pythonpath()
            dlg = PathManager(self, pathlist, sync=False)
            dlg.exec_()
            project.set_pythonpath(dlg.get_path_list())
            self.parent_widget.emit(SIGNAL("pythonpath_changed()"))
    
    def edit_related_projects(self, projects):
        title = translate('ProjectExplorer', 'Related projects')
        for project in projects:
            related_projects = project.get_related_projects()
            data = []
            other_projects = [_p for _p in self.projects if _p is not project]
            for proj in other_projects:
                name = proj.get_name()
                data.append((name, name in related_projects))
            comment = translate('ProjectExplorer',
                                "Select projects which are related to "
                                "<b>%1</b>").arg(project.get_name())
            result = fedit(data, title=title, comment=comment)
            if result is not None:
                related_projects = []
                for index, is_related in enumerate(result):
                    if is_related:
                        name = other_projects[index].get_name()
                        related_projects.append(name)
                project.set_related_projects(related_projects)
    
    def show_properties(self, items):
        pathlist = sorted([get_item_path(_it) for _it in items])
        dirlist = [path for path in pathlist if osp.isdir(path)]
        for path in pathlist[:]:
            for folder in dirlist:
                if path != folder and path.startswith(folder):
                    pathlist.pop(pathlist.index(path))
        files, lines = 0, 0
        for path in pathlist:
            f, l = count_lines(path)
            files += f
            lines += l
        QMessageBox.information(self, translate('ProjectExplorer',
                                                "Project Explorer"),
                                translate('ProjectExplorer',
                                          "Statistics on source files only:<br>"
                                          "(Python, C/C++, Fortran)<br><br>"
                                          "<b>%1</b> files.<br>"
                                          "<b>%2</b> lines of code.") \
                                .arg(str(files)).arg(str(lines)))
        
    def open_windows_explorer(self, items):
        for path in sorted([get_item_path(_it) for _it in items]):
            os.startfile(path)
        
    def open_terminal(self, items):
        for path in sorted([get_item_path(_it) for _it in items]):
            self.parent_widget.emit(SIGNAL("open_terminal(QString)"), path)
            
    def open_interpreter(self, items):
        for path in sorted([get_item_path(_it) for _it in items]):
            self.parent_widget.emit(SIGNAL("open_interpreter(QString)"), path)
            
    def open_ipython(self, items):
        for path in sorted([get_item_path(_it) for _it in items]):
            self.parent_widget.emit(SIGNAL("open_ipython(QString)"), path)
        
    def refresh(self, clear=True):
#        if clear:
#            self.clear()
        for project in self.projects:
            project.refresh(self, self.include, self.exclude, self.show_all)
            
    #---- Internal drag & drop
    def supportedDropActions(self):
        """Reimplement Qt method"""
        return Qt.MoveAction | Qt.CopyAction
    
    def mimeData(self, items):
        """Reimplement Qt method"""
        data = super(ExplorerTreeWidget, self).mimeData(items)
        data.setUrls([QUrl(get_item_path(item)) for item in items])
        return data
    
    def dragMoveEvent(self, event):
        """Reimplement Qt method"""
        item = self.itemAt(event.pos())
        if item is None:
            event.ignore()
        else:
            dst = get_item_path(item)
            if osp.isdir(dst):
                event.acceptProposedAction()
            else:
                event.ignore()

    def dropEvent(self, event):
        """Reimplement Qt method"""
        event.ignore()
        action = event.dropAction()
        if action not in (Qt.MoveAction, Qt.CopyAction):
            return
        
#        # QTreeWidget must not remove the source items even in MoveAction mode:
#        event.setDropAction(Qt.CopyAction)
        
        dst = get_item_path(self.itemAt(event.pos()))
        yes_to_all, no_to_all = None, None
        src_list = [unicode(url.toString()) for url in event.mimeData().urls()]
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
                    answer = QMessageBox.warning(self,
                            translate('ProjectExplorer', 'Project explorer'),
                            translate('ProjectExplorer',
                                      'File <b>%2</b> already exists.<br>'
                                      'Do you want to overwrite it?') \
                                      .arg(dst_fname), buttons)
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
                    QMessageBox.critical(self, translate('ProjectExplorer',
                                                         'Project explorer'),
                                         translate('ProjectExplorer', 'Folder '
                                                   '<b>%2</b> already exists.')\
                                         .arg(dst_fname), QMessageBox.Ok)
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
                        move_file(src, dst)
                    else:
                        shutil.move(src, dst)
                    self.parent_widget.emit(SIGNAL("removed(QString)"), src)
            except EnvironmentError, error:
                if action == Qt.CopyAction:
                    action_str = translate('ProjectExplorer', 'copy')
                else:
                    action_str = translate('ProjectExplorer', 'move')
                QMessageBox.critical(self,
                    translate('ProjectExplorer', "Project Explorer"),
                    translate('ProjectExplorer',
                              "<b>Unable to %1 <i>%2</i></b>"
                              "<br><br>Error message:<br>%3") \
                    .arg(action_str).arg(src).arg(str(error)))
                    
#            print str(func)+":", src, "to:", dst


class ProjectExplorerWidget(QWidget):
    """
    Project Explorer
    
    Signals:
        SIGNAL("open_file(QString)")
        SIGNAL("create_module(QString)")
        SIGNAL("pythonpath_changed()")
        SIGNAL("renamed(QString,QString)")
        SIGNAL("removed(QString)")
    """
    def __init__(self, parent=None, include='.', exclude=r'\.pyc$|^\.',
                 show_all=False, valid_types=['.py', '.pyw']):
        QWidget.__init__(self, parent)
        
        self.treewidget = ExplorerTreeWidget(self)
        self.treewidget.setup(include=include, exclude=exclude,
                              show_all=show_all, valid_types=valid_types)

        filters_action = create_toolbutton(self, get_icon('filter.png'),
                                           tip=translate('ProjectExplorer',
                                                   "Edit filename filter..."),
                                           triggered=self.edit_filter)
        # Show all files
        all_action = create_toolbutton(self, get_icon('show_all.png'),
                                       tip=translate('ProjectExplorer',
                                                     "Show all files"),
                                       toggled=self.toggle_all)
        all_action.setChecked(show_all)
        
        refresh_btn = create_toolbutton(self,
                        tip=translate('ProjectExplorer', "Refresh"),
                        icon=get_icon('reload.png'),
                        triggered=lambda: self.treewidget.refresh(clear=True))
        
        collapse_btn = create_toolbutton(self, text_beside_icon=False)
        collapse_btn.setDefaultAction(self.treewidget.collapse_selection_action)
        expand_btn = create_toolbutton(self, text_beside_icon=False)
        expand_btn.setDefaultAction(self.treewidget.expand_selection_action)
        restore_btn = create_toolbutton(self, text_beside_icon=False)
        restore_btn.setDefaultAction(self.treewidget.restore_action)
        
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignRight)
        for btn in (filters_action, all_action, refresh_btn,
                    collapse_btn, expand_btn, restore_btn):
            btn_layout.addWidget(btn)

        layout = QVBoxLayout()
        layout.addWidget(self.treewidget)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
    def add_project(self, project):
        return self.treewidget.add_project(project)
        
    def get_project_config(self):
        projects = self.treewidget.projects
        return [_proj.get_root_path() for _proj in projects]
    
    def set_project_config(self, data):
        for root_path in data:
            if osp.isdir(root_path):
                #XXX: It would be better to add the project anyway but to 
                # notify the user that it's not valid (red icon...)
                self.add_project(root_path)

    def get_pythonpath(self):
        return self.treewidget.get_pythonpath()

    def edit_filter(self):
        """Edit include/exclude filter"""
        include, exclude = self.treewidget.include, self.treewidget.exclude
        filter = [(translate('ProjectExplorer', 'Type'),
                   [True, (True, translate('ProjectExplorer',
                                           'regular expressions')),
                    (False, translate('ProjectExplorer', 'global patterns'))]),
                  (translate('ProjectExplorer', 'Include'), include),
                  (translate('ProjectExplorer', 'Exclude'), exclude),]
        result = fedit(filter,
                       title=translate('ProjectExplorer', 'Edit filter'),
                       parent=self)
        if result:
            regexp, include, exclude = result
            if not regexp:
                import fnmatch
                include = fnmatch.translate(include)
                exclude = fnmatch.translate(exclude)
            self.emit(SIGNAL('option_changed'), 'include', include)
            self.emit(SIGNAL('option_changed'), 'exclude', exclude)
            self.treewidget.include, self.treewidget.exclude = include, exclude
            self.treewidget.refresh()
            
    def toggle_all(self, checked, refresh=True):
        """Toggle all files mode"""
        self.emit(SIGNAL('option_changed'), 'show_all', checked)
        self.treewidget.show_all = checked
        self.treewidget.refresh()


class Test(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        vlayout = QVBoxLayout()
        self.setLayout(vlayout)
        
        self.explorer = ProjectExplorerWidget()
        p1 = self.explorer.add_project(r"D:\Python\spyder")
#        p1.set_pythonpath([r"D:\Python\spyder\spyderlib"])
#        p1.save()
#        self.treewidget.close_project(p1)
#        _p2 = self.explorer.add_project(r"D:\Python\test_project")
        
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
        
        hlayout3 = QHBoxLayout()
        vlayout.addLayout(hlayout3)
        label = QLabel("<b>Option changed:</b>")
        label.setAlignment(Qt.AlignRight)
        hlayout3.addWidget(label)
        self.label3 = QLabel()
        hlayout3.addWidget(self.label3)
        self.connect(self.explorer, SIGNAL("option_changed"),
           lambda x, y: self.label3.setText('option_changed: %r, %r' % (x, y)))

if __name__ == "__main__":
    from spyderlib.utils.qthelpers import qapplication
    _app = qapplication()
    test = Test()
    test.exec_()

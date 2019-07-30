# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tree model for use with multiple filesystem nodes."""

# Local imports
from __future__ import unicode_literals
import os
import os.path as osp

# Third party imports
from qtpy.QtCore import (QAbstractItemModel, QDir, QFileInfo, QModelIndex, Qt,
                         Signal, Slot)
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QApplication, QFileIconProvider, QTreeView

# Local imports
from spyder.plugins.projects.utils.watcher import WorkspaceWatcher


class FileSystemNode(object):
    """
    Internal data representation of a multi file system tree model.
    """

    def __init__(self, data):
        """
        Internal data representation of a multi file system tree model.
        """
        # Variables
        self._data = self._check_data(data)
        self._parent = None
        self._children = []
        self._row = 0
        self._columncount = 4  # len(self._data)

        # Need to be updated every time a root node is created!
        self._icon_provider = None
        self._is_dir = None
        self._is_root_name = False
        self._fileinfo = None
        self._fullpath = None
        self._qdir = None
        self._root_name_node = None

    def _check_data(self, data):
        """Check that data has the correct format."""
        if isinstance(data, (tuple, list)):
            data = list(data)
        else:
            raise ValueError('"data" must be a list or tuple!')

        return data

    def __str__(self):
        return "FileSystemNode({0})".format(self._data)

    def __repr__(self):
        return "FileSystemNode({0})".format(self._data)

    # --- Required Qt API
    # ------------------------------------------------------------------------
    def data(self, column):
        """Return the node data for given column."""
        if column >= 0 and column < len(self._data):
            return self._data[column]

    def columnCount(self):
        """Return the column count."""
        return self._columncount

    def childCount(self):
        """Return the child count."""
        return len(self._children)

    def child(self, row):
        """Return the child for given row."""
        if row >= 0 and row < self.childCount():
            return self._children[row]

    def parent(self):
        """Return the parent node."""
        return self._parent

    def row(self):
        """Return the row occupied by this node within its parent."""
        return self._row

    def addChild(self, child):
        """Add child to node."""
        child._parent = self
        child._row = len(self._children)
        self._children.append(child)
        self._columncount = max(child.columnCount(), self._columncount)

    # --- API
    # ------------------------------------------------------------------------
    @staticmethod
    def human_size(size):
        """Convert file size to human readable format."""
        units = ['bytes', 'KB', 'MB', 'GB', 'TB']
        for unit in units:
            if size >= 1024.0:
                size /= 1024.0
            else:
                break
        return '{0:.0f} {1}'.format(size, unit)

    def update_data(self, fullpath, is_root_name=False):
        """"""
        self._fullpath = fullpath
        self._fileinfo = QFileInfo(fullpath)
        name = self._data[0] if is_root_name else osp.basename(fullpath)

        self._data = [
            name,
            FileSystemNode.human_size(self._fileinfo.size()),
            self._icon_provider.type(self._fileinfo),
            self._fileinfo.lastModified(),
        ]

    def set_path(self, path, paths):
        """
        Set the path of the node and create the children recursively.
        """
        self._path = path
        self._qdir.setPath(path)
        items = self._qdir.entryList()

        for item in items:
            fullpath = os.path.join(path, item)
            fileinfo = QFileInfo(fullpath)
            data = [
                item,
                FileSystemNode.human_size(fileinfo.size()),
                self._icon_provider.type(fileinfo),
                fileinfo.lastModified(),
            ]
            node = FileSystemNode(data)
            node._icon_provider = self._icon_provider
            node._fileinfo = fileinfo
            node._fullpath = fullpath
            node._qdir = self._qdir
            node._root_name_node = self._root_name_node

            self.addChild(node)
            paths.add(fullpath)
            if os.path.isdir(fullpath):
                node._is_dir = True
                node.set_path(fullpath, paths)
            else:
                node._is_dir = False

        # Add the actual path
        paths.add(path)
        return paths


class MultiFileSystemModel(QAbstractItemModel):
    """"""

    # Enums
    ColumnName = 0
    ColumnSize = 1
    ColumnType = 2
    ColumnLastModified = 3

    # Expose similar iterface to QFileSystemModel
    directoryLoaded = Signal(object)
    fileRenamed = Signal(object, object, object)
    rootPathChanged = Signal(object)
    modelReset = Signal()

    # Watcher signals
    sig_file_created = Signal(object, bool)
    sig_file_deleted = Signal(object, bool)
    sig_file_modified = Signal(object, bool)
    sig_file_moved = Signal(object, object, bool)

    def __init__(self):
        """"""
        super(MultiFileSystemModel, self).__init__()

        # Root tree node has no parent or data
        self._root = FileSystemNode([None])

        # Watch file system for changes and notify them
        self._watchers = {}
        self._watcher_paths = {}

        # To avoid creating and querying the same icon over and over
        self._icon_cache = {'__': QIcon()}

        self._icon_provider = QFileIconProvider()
        self._filters = QDir.AllEntries | QDir.NoDotAndDotDot | QDir.AllDirs
        self._name_filter = ''
        self._sort_flags = QDir.Name | QDir.IgnoreCase
        self._qdir = self._make_qdir()
        self._name_filter_disables = True
        self._sorted_column = self.ColumnType
        self._sorted_order = Qt.DescendingOrder

    # --- Helpers
    def _created(self, path, is_dir, root_name_node):
        """"""
        root_name = root_name_node.data(self.ColumnName)

        # If a file filter it using QDir
        if osp.isfile(path):
            parent_path = osp.dirname(path)
            self._qdir.setPath(parent_path)
            paths = self._qdir.entryList()
            path = path if osp.basename(path) in paths else []

        if path and path not in self._watcher_paths[root_name]:
            parent_path = osp.dirname(path)
            parent_index = self.index(parent_path, self.ColumnName, root_name)

            if parent_index:
                parent_node = parent_index.internalPointer()

                name = osp.basename(path)
                fileinfo = QFileInfo(path)
                node = FileSystemNode([name])
                node._icon_provider = self._icon_provider
                node._is_dir = is_dir
                node._fileinfo = fileinfo
                node._fullpath = path
                node._qdir = self._qdir
                node._root_name_node = root_name_node
                node.update_data(path, node._is_root_name)

                row = len(parent_node._children)
                self.beginInsertRows(parent_index, row, row)
                parent_node.addChild(node)
                new_paths = node.set_path(path, set())
                old_paths = self._watcher_paths[root_name]
                self._watcher_paths[root_name] = old_paths.union(new_paths)
                self.endInsertRows()

                # # Is this needed?
                self.sort(self._sorted_column, self._sorted_order)

    def _deleted(self, path, is_dir, root_name_node):
        """Handle path or file deletion."""
        root_name = root_name_node.data(self.ColumnName)
        if path in self._watcher_paths[root_name]:
            index = self.index(path, self.ColumnName, root_name)
            if index:
                node = index.internalPointer()
                parent_index = index.parent()
                parent_node = node.parent()

                for idx, child in enumerate(parent_node._children):
                    if child._fullpath == path:
                        row = idx
                        break
                else:
                    row = None

                if row is not None:
                    self.beginRemoveRows(parent_index, row, row)
                    self._watcher_paths[root_name].remove(path)
                    parent_node._children.pop(row)
                    self.endRemoveRows()

    def _modified(self, path, is_dir, root_name_node):
        """"""
        name = root_name_node.data(self.ColumnName)
        if path in self._watcher_paths[name]:
            index = self.index(path, self.ColumnName, name)
            node = index.internalPointer()

            # Do not update the extra columns for root_name_node
            if root_name_node._fullpath != path:
                node.update_data(path, node._is_root_name)
            # self.dataChanged.emit()

    def _moved(self, src_path, dest_path, is_dir, root_name_node):
        """"""
        root_name = root_name_node.data(self.ColumnName)
        if src_path in self._watcher_paths[root_name]:
            self._created(dest_path, is_dir, root_name_node)
            self._deleted(src_path, is_dir, root_name_node)

    def _check_root_name(self, name):
        if name in self._watchers:
            raise ValueError('Root `name` must be unique on the model!')
        return name

    def _make_qdir(self):
        """"""
        return QDir('', self._name_filter, self._sort_flags, self._filters)

    def _create_path_index_map(self, path, column, parent_index, dic):
        """"""
        # TODO: this is expensive right now, create at startup and recreate
        # on file chages only
        parent_node = parent_index.internalPointer()
        for row in range(parent_node.childCount()):
            child_index = self.index(row, column, parent_index)
            child_node = child_index.internalPointer()
            dic[child_node._fullpath] = child_index
            self._create_path_index_map(path, column, child_index, dic)

        # Include the parent_index
        parent_path = parent_index.internalPointer()._fullpath
        dic[parent_path] = parent_index

        return dic

    def _index_for_root_name(self, root_name):
        """"""
        if root_name not in self._watchers:
            error = 'root_name "{}" does not exist!'.format(root_name)
            raise ValueError(error)

        parent_index = QModelIndex()
        for row in range(self._root.childCount()):
            child_index = self.index(row, self.ColumnName, parent_index)
            child_node = child_index.internalPointer()
            if child_node.data(self.ColumnName) == root_name:
                return child_index

    def _index_for_path(self, path, column, root_name):
        """Return the model index for the given path, column and root_name."""
        root_name_index = self._index_for_root_name(root_name)
        if root_name_index:
            dic = self._create_path_index_map(path, column, root_name_index,
                                              {})
            return dic.get(path)

    def _index(self, row, column, parent_index=None):
        """
        Return the index for `row`, `column` and optional `parent_index`.
        """
        if not parent_index or not parent_index.isValid():
            parent_node = self._root
        else:
            parent_node = parent_index.internalPointer()

        if not QAbstractItemModel.hasIndex(self, row, column, parent_index):
            return QModelIndex()

        child_node = parent_node.child(row)
        if child_node:
            index =  QAbstractItemModel.createIndex(self, row, column,
                                                    child_node)
            return index
        else:
            return QModelIndex()

    def _sort(self, node, column, reverse=False):
        """Sort helper to provide recursive sorting of nodes."""
        # Sort by column and name

        # QDir::Name	0x00	Sort by name.
        # QDir::Time	0x01	Sort by time (modification time).
        # QDir::Size	0x02	Sort by file size.
        # QDir::Type	0x80	Sort by file type (extension).
        # QDir::Unsorted	0x03	Do not sort.
        # QDir::NoSort	-1	Not sorted by default.
        # QDir::DirsFirst	0x04	Put the directories first, then the files.
        # QDir::DirsLast	0x20	Put the files first, then the directories.
        # QDir::Reversed	0x08	Reverse the sort order.
        # QDir::IgnoreCase	0x10	Sort case-insensitively.
        # QDir::LocaleAware	0x40	Sort items appropriately using the current locale settings.

        # sort_flag_options = {
        #     self.ColumnName: QDir.Name,
        #     self.ColumnType: QDir.Type,
        #     self.ColumnSize: QDir.Size,
        #     self.ColumnLastModified: QDir.Time,
        # }
        # sort_flags = self._sort_flags | sort_flag_options[column]
        # if reverse:
        #     sort_flags |= QDir.Reversed

        # if node._is_dir:
        #     self._sorting_qdir = QDir(node._fullpath, self._name_filter,
        #                               sort_flags, self._filters)
        #     # Use this order to sort the files!
        #     filenames = self._sorting_qdir.entryList()
        #     name_child_map = {}
        #     for child in node._children:
        #         name_child_map[child.data(self.ColumnName)] = child
        #     new_sorted_children = [name_child_map[fn] for fn in filenames]
        #     node._children = new_sorted_children

        if node.data(column) is None or column == self.ColumnLastModified:
            node._children.sort(
                key=lambda n: (n.data(column),
                            n.data(self.ColumnName).lower()),
                reverse=reverse,
            )
        else:
            node._children.sort(
                key=lambda n: (n.data(column).lower(),
                            n.data(self.ColumnName).lower()),
                reverse=reverse,
            )
        for child in node._children:
            self._sort(child, column, reverse)

    def _fix_presistent_data(self):
        """"""
        persistent_index_data = []
        for idx in self.persistentIndexList():
            node = idx.internalPointer()
            persistent_index_data.append(
                (idx, node._fullpath, node.data(self.ColumnName),
                 node._root_name_node)
            )

        old_idx_list = []
        new_idx_list = []
        for data in persistent_index_data:
            old_idx, fullpath, root_name, root_name_node = data
            if root_name is not None:
                if root_name_node is None:
                    new_idx = self._index_for_root_name(root_name)
                else:
                    new_idx = self.index(fullpath, self.ColumnName,
                                         root_name_node.data(self.ColumnName))
                old_idx_list.append(old_idx)
                new_idx_list.append(new_idx)
            else:
                print('error', data)
        self.changePersistentIndexList(old_idx_list, new_idx_list)

    # --- API
    def rowCount(self, index):
        """Return the row count for the given model index."""
        node = index.internalPointer() if index.isValid() else self._root
        return node.childCount()

    def addChild(self, node, parent_index):
        """"""
        if not parent_index or not parent_index.isValid():
            parent_node = self._root
        else:
            parent_node = parent_index.internalPointer()

        parent_node.addChild(node)

    @Slot(int, int, QModelIndex)
    @Slot(object, int, object)  # object -> string
    def index(self, row_or_path, column, parent_index_or_root_name):
        """"""
        if isinstance(row_or_path, int):
            return self._index(row_or_path, column, parent_index_or_root_name)
        else:
            return self._index_for_path(row_or_path, column,
                                        parent_index_or_root_name)

    def parent(self, index):
        """Return the parent for the given model index."""
        if index.isValid():
            p = index.internalPointer().parent()
            if p:
                return QAbstractItemModel.createIndex(self, p.row(), 
                                                      self.ColumnName, p)
        return QModelIndex()

    def columnCount(self, index):
        """Return the column count."""
        if index.isValid():
            node = index.internalPointer()
            return node.columnCount()

        return self._root.columnCount()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """"""
        # TODO: This changes based on OS
        headers = {
            self.ColumnName: 'Name',
            self.ColumnSize: 'Size',
            self.ColumnType: 'Kind',
            self.ColumnLastModified: 'Date modified',
        }
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
               return  headers.get(section)

    def data(self, index, role):
        """Return data for the given index and role."""
        if not index.isValid():
            return None

        node = index.internalPointer()
        column = index.column()

        if role == Qt.DisplayRole:
            return node.data(column)

        if role == Qt.DecorationRole:
            if column == self.ColumnName:
                fullpath = node._fullpath

                if fullpath is None:
                    icon = QIcon()
                elif node._is_root_name:
                    icon = self._icon_provider.icon(
                        QFileIconProvider.Computer)
                else:
                    finfo = QFileInfo(node._fullpath)
                    icon = self._icon_provider.icon(finfo)
                return icon

        if role == Qt.TextAlignmentRole:
            if column == self.ColumnSize:
                return Qt.AlignRight
            else:
                return Qt.AlignLeft

        return None

    def sort(self, column, order=Qt.AscendingOrder):
        """Sort the model by `column` and given `order`."""
        self.layoutAboutToBeChanged.emit()

        self._sorted_column = column
        self._sorted_order = order

        # Do actual sort
        reverse = order == Qt.AscendingOrder
        self._sort(self._root, column, reverse)
        self._fix_presistent_data()
        self.layoutChanged.emit()

    # --- QFileSystemModel API
    def iconProvider(self, icon_provider):
        """Return the current icon provider."""
        return self._icon_provider

    def setIconProvider(self, icon_provider):
        """Set the model icon provider."""
        self._icon_provider = icon_provider

    def filePath(self, index):
        """"""
        if index.isValid():
            node = index.internalPointer()
            return node._fullpath

    def filter(self):
        """"""
        return self._filters

    def setFilter(self, filters):
        """"""
        self._filters = filters

    def nameFilters(self, filters):
        """"""
        return self._name_filter

    def setNameFilters(self, filters):
        """"""
        self._name_filter = filters

    def nameFilterDisables(self):
        """"""
        # This is not supported but provided for compatibility with 
        # QFileSystemModel
        return self._name_filter_disables

    def setNameFilterDisables(self, value):
        """"""
        # This is not supported but provided for compatibility with 
        # QFileSystemModel
        self._name_filter_disables = value

    def setRootPath(self, path, root_name=None):
        """
        This method is named as the FileSystemModel one but needs to provide
        a `root_name`.
        """
        if root_name is None:
            raise Exception
        else:
            self.add_root_path(root_name, path)

    def rootPath(self, root_name=None):
        """
        This method is named as the FileSystemModel one but needs to provide
        a `root_name`.
        """
        if root_name is None:
            raise Exception
        else:
            index = self._index_for_root_name(root_name)
            node = index.internalPointer()
            return node._fullpath

    # --- Addititional API
    def add_root_path(self, name, path):
        """Add a root node with `name` and given root `path`."""
        name = self._check_root_name(name)
        if osp.isdir(path):
            watcher = WorkspaceWatcher(self)

            node = FileSystemNode([name])
            node._icon_provider = self._icon_provider
            node._is_dir = True
            node._is_root_name = True
            node._fileinfo = QFileInfo(path)
            node._fullpath = path
            node._qdir = self._qdir
            node._root_name_node = node

            # Connect to handler signals
            watcher.sig_file_created.connect(
                lambda p, d: self._created(p, d, node))
            watcher.sig_file_deleted.connect(
                lambda p, d: self._deleted(p, d, node))
            watcher.sig_file_modified.connect(
                lambda p, d: self._modified(p, d, node))
            watcher.sig_file_moved.connect(
                lambda sp, dp, d: self._moved(sp, dp, d, node))

            # Connect to model signals
            watcher.sig_file_created.connect(self.sig_file_created)
            watcher.sig_file_deleted.connect(self.sig_file_deleted)
            watcher.sig_file_modified.connect(self.sig_file_modified)
            watcher.sig_file_moved.connect(self.sig_file_moved)

            # This should be done in a thread to avoid locking the GUI
            paths = node.set_path(path, set())
            self._watcher_paths[name] = paths
            self._watchers[name] = watcher
            watcher.start(path)
            self.directoryLoaded.emit(path)
            self._root.addChild(node)

            # Sort by type
            self.sort(self.ColumnType, order=Qt.DescendingOrder)

    def update_root_name(self, old_name, new_name):
        """Update the root name."""
        new_name = self._check_root_name(new_name)

        # Update value for root node :-)
        index = self._index_for_root_name(old_name)
        node = index.internalPointer()
        node._data = [new_name, '', '', '']

        # Need to update key for watchers and watchers paths
        self._watchers[new_name] = self._watchers.pop(old_name)
        self._watcher_paths[new_name] = self._watcher_paths.pop(old_name)
        self.dataChanged.emit(index, index)
        self.sort(self._sorted_column, self._sorted_order)  # needed?


class TreeView(QTreeView):
    pass


def main():
    import qdarkstyle

    v = TreeView()
    dark_qss = qdarkstyle.load_stylesheet_from_environment()
    # v.setStyleSheet(dark_qss)
    v.setSortingEnabled(True)
    # v.setHeaderHidden(True)
    model = MultiFileSystemModel()
    v.setModel(model)
    model.add_root_path(name='project-2', path='/Users/gpena-castellanos/Downloads/')
    model.add_root_path(name='project-3', path='/Users/gpena-castellanos/Google Drive/develop/quansight/spyder')
    model.add_root_path(name='project-4', path='/Users/gpena-castellanos/Google Drive/develop/quansight/QDarkStyleSheet')
    v.show()
    return v


if __name__ == '__main__':
    app = QApplication([])
    v = main()
    path = '/Users/gpena-castellanos/Google Drive/develop/quansight/spyder'
    path = '/Users/gpena-castellanos/Downloads/Image from iOS1.jpg'
    path = '/Users/gpena-castellanos/Google Drive/develop/quansight/QDarkStyleSheet'
    # print(v.model().index(path, 0, 'project-2'))
    # v.model().update_root_name('project-4', 'project-0')
    # print(v.model().index(path, 0, 'project-4'))
    app.exec_()

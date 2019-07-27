# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tree model for use with multiple filesystem nodes."""

# Local imports
import os
import os.path as osp

# Third party imports
from qtpy.QtCore import Qt, QAbstractItemModel, QModelIndex, QFileSystemWatcher, Signal, Slot, QFileInfo
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QApplication, QTreeView, QFileIconProvider

# Local imports
from spyder.utils import icon_manager as ima


class FileSystemNode(object):
    """"""

    def __init__(self, data):
        """"""
        # Variables
        self._data = self._check_data(data)
        self._fs = None
        self._is_dir = None
        self._fullpath = None
        self._parent = None
        self._columncount = len(self._data)
        self._children = []
        self._row = 0

    def _check_data(self, data):
        """Check that data has the correct format."""
        if isinstance(data, (tuple, list)):
            data = list(data)
        else:
            raise ValueError('"data" must be a list or tupple!')

        return data

    # --- Required Qt API
    # ------------------------------------------------------------------------
    def data(self, column):
        """Return the node data for given column."""
        if column >= 0 and column < len(self._data):
            return self._data[column]

    def columnCount(self):
        """Return the column count."""
        return 1

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
        """???."""
        return self._row

    def addChild(self, child):
        """Add child to node."""
        child._parent = self
        child._row = len(self._children)
        self._children.append(child)
        self._columncount = max(child.columnCount(), self._columncount)

    # --- API
    # ------------------------------------------------------------------------
    def set_path(self, path, paths):
        """"""
        self._path = path
        items = sorted(os.listdir(path), reverse=True)
        for item in items:
            node = FileSystemNode([item])
            fullpath = os.path.join(path, item)
            self.addChild(node)
            paths.append(fullpath)
            node._fullpath = fullpath
            if os.path.isdir(fullpath):
                node._is_dir = True
                node.set_path(fullpath, paths)
            else:
                node._is_dir = False

        return paths


class MultiFileSystemModel(QAbstractItemModel):
    """"""

    # Expose similar iterface to QFileSystemModel
    directoryLoaded = Signal(object)
    fileRenamed = Signal(object, object, object)
    rootPathChanged = Signal(object)
    modelReset = Signal()

    def __init__(self):
        """"""
        super(MultiFileSystemModel, self).__init__()

        # Root tree node has no parent or data
        self._root = FileSystemNode([None])

        # Watch file system for changes and notify them
        self._watchers = {}

        # To avoid creating and querying the same icon over and over
        self._icon_cache = {'__': QIcon()}

        self._icon_provider = QFileIconProvider()
        self._model_index = {}

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

    def _index_for_path(self, path, column):
        """"""
        return self._model_index.get((path, column), QModelIndex())

    def _index(self, row, column, parent_index=None):
        """"""
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

            self._model_index[(child_node._fullpath, column)] = index
            return index
        else:
            return QModelIndex()

    @Slot(object, int)
    @Slot(int, int, QModelIndex)
    def index(self, row_or_path, column, parent_index=None):
        """"""
        if isinstance(row_or_path, int):
            return self._index(row_or_path, column, parent_index)
        else:
            return self._index_for_path(row_or_path, column)

    def parent(self, index):
        """Return the parent for the given model index."""
        if index.isValid():
            p = index.internalPointer().parent()
            if p:
                return QAbstractItemModel.createIndex(self, p.row(), 0, p)

        return QModelIndex()

    def columnCount(self, index):
        """Return the column count."""
        if index.isValid():
            node = index.internalPointer()
            return node.columnCount()

        return self._root.columnCount()

    def data(self, index, role):
        """Return data for the given index and role."""
        if not index.isValid():
            return None

        node = index.internalPointer()

        if role == Qt.DisplayRole:
            return node.data(index.column())

        # Define icon for item
        if role == Qt.DecorationRole:
            fullpath = node._fullpath
            if fullpath is None:
                icon = QIcon()
            else:
                finfo = QFileInfo(node._fullpath)
                icon = self._icon_provider.icon(finfo)
            return icon

        return None

    def sort(self, column, order=Qt.AscendingOrder):
        self.layoutAboutToBeChanged.emit()
        reverse = order == Qt.AscendingOrder
        self._sort(self._root, column, reverse)
        self.layoutChanged.emit()

    def _sort(self, node, column, reverse=False):
        # old_list = self.persistentIndexList()
        node._children.sort(key=lambda n: n.data(column), reverse=reverse)
        # self.changePersistentIndexList(old_list, new_list)
        for child in node._children:
            self._sort(child, column, reverse)

    # --- QFileSystemModel API
    def iconProvider(self, icon_provider):
        """"""
        return self._icon_provider

    def setIconProvider(self, icon_provider):
        """"""
        self._icon_provider = icon_provider

    def setFilter(self, filters):
        """"""

    def setNameFilterDisables(self, value):
        """"""

    def setNameFilters(self, filters):
        """"""

    def filePath(self, index):
        """"""
        if index.isValid():
            node = index.internalPointer()
            return node._fullpath

    def setRootPath(self, index):
        """"""

    def rootPath(self, index):
        """"""

    # --- Addititional API
    def add_root_path(self, name, path):
        """"""
        if osp.isdir(path):
            watcher = QFileSystemWatcher(self)
            watcher.fileChanged.connect(lambda p, w=watcher: self._file_changed(path, w))
            watcher.directoryChanged.connect(lambda p, w=watcher: self._directory_changed(path, w))

            paths = []

            # This should be done in a thread to avoid locking the GUI
            node = FileSystemNode([name])
            paths = node.set_path(path, paths)
            self.directoryLoaded.emit(path)
            watcher.addPaths(paths)
            self._root.addChild(node)

        self._watchers[name] = watcher

    def _directory_changed(self, path, watcher):
        """"""
        print(watcher, path)

    def _file_changed(self, path, watcher):
        """"""
        print(watcher, path)


class TreeView(QTreeView):
    pass


def main():
    import qdarkstyle

    v = TreeView()
    dark_qss = qdarkstyle.load_stylesheet_from_environment()
    v.setStyleSheet(dark_qss)
    v.setSortingEnabled(True)
    # v.setHeaderHidden(True)
    model = MultiFileSystemModel()
    v.setModel(model)
    model.add_root_path(name='project-1', path='/Users/gpena-castellanos/tester2/')
    model.add_root_path(name='project-2', path='/Users/gpena-castellanos/Downloads/')
    model.add_root_path(name='project-3', path='/Users/gpena-castellanos/Google Drive/develop/quansight/spyder')
    model.add_root_path(name='project-4', path='/Users/gpena-castellanos/Google Drive/develop/quansight/QDarkStyleSheet')

    v.show()
    return v

app = QApplication([])
v = main()
path = '/Users/gpena-castellanos/Downloads/Image from iOS1.jpg'
app.exec_()

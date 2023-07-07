# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Project Explorer"""

# pylint: disable=C0103

# Standard library imports
import os
import os.path as osp
import shutil

# Third party imports
from qtpy.QtCore import QSortFilterProxyModel, Qt, Signal, Slot
from qtpy.QtWidgets import QAbstractItemView, QHeaderView, QMessageBox

# Local imports
from spyder.api.translations import _
from spyder.py3compat import to_text_string
from spyder.utils import misc
from spyder.plugins.explorer.widgets.explorer import DirView


class ProxyModel(QSortFilterProxyModel):
    """Proxy model to filter tree view."""

    PATHS_TO_HIDE = [
        # Useful paths
        '.spyproject',
        '__pycache__',
        '.ipynb_checkpoints',
        # VCS paths
        '.git',
        '.hg',
        '.svn',
        # Others
        '.pytest_cache',
        '.DS_Store',
        'Thumbs.db',
        '.directory'
    ]

    PATHS_TO_SHOW = [
        '.github'
    ]

    def __init__(self, parent):
        """Initialize the proxy model."""
        super(ProxyModel, self).__init__(parent)
        self.root_path = None
        self.path_list = []
        self.setDynamicSortFilter(True)

    def setup_filter(self, root_path, path_list):
        """
        Setup proxy model filter parameters.

        Parameters
        ----------
        root_path: str
            Root path of the proxy model.
        path_list: list
            List with all the paths.
        """
        self.root_path = osp.normpath(str(root_path))
        self.path_list = [osp.normpath(str(p)) for p in path_list]
        self.invalidateFilter()

    def sort(self, column, order=Qt.AscendingOrder):
        """Reimplement Qt method."""
        self.sourceModel().sort(column, order)

    def filterAcceptsRow(self, row, parent_index):
        """Reimplement Qt method."""
        if self.root_path is None:
            return True
        index = self.sourceModel().index(row, 0, parent_index)
        path = osp.normcase(osp.normpath(
            str(self.sourceModel().filePath(index))))

        if osp.normcase(self.root_path).startswith(path):
            # This is necessary because parent folders need to be scanned
            return True
        else:
            for p in [osp.normcase(p) for p in self.path_list]:
                if path == p or path.startswith(p + os.sep):
                    if not any([path.endswith(os.sep + d)
                                for d in self.PATHS_TO_SHOW]):
                        if any([path.endswith(os.sep + d)
                                for d in self.PATHS_TO_HIDE]):
                            return False
                        else:
                            return True
                    else:
                        return True
            else:
                return False

    def data(self, index, role):
        """Show tooltip with full path only for the root directory."""
        if role == Qt.ToolTipRole:
            root_dir = self.path_list[0].split(osp.sep)[-1]
            if index.data() == root_dir:
                return osp.join(self.root_path, root_dir)
        return QSortFilterProxyModel.data(self, index, role)

    def type(self, index):
        """
        Returns the type of file for the given index.

        Parameters
        ----------
        index: int
            Given index to search its type.
        """
        return self.sourceModel().type(self.mapToSource(index))


class FilteredDirView(DirView):
    """Filtered file/directory tree view."""
    def __init__(self, parent=None):
        """Initialize the filtered dir view."""
        super().__init__(parent)
        self.proxymodel = None
        self.setup_proxy_model()
        self.root_path = None

    # ---- Model
    def setup_proxy_model(self):
        """Setup proxy model."""
        self.proxymodel = ProxyModel(self)
        self.proxymodel.setSourceModel(self.fsmodel)

    def install_model(self):
        """Install proxy model."""
        if self.root_path is not None:
            self.setModel(self.proxymodel)

    def set_root_path(self, root_path):
        """
        Set root path.

        Parameters
        ----------
        root_path: str
            New path directory.
        """
        self.root_path = root_path
        self.install_model()
        index = self.fsmodel.setRootPath(root_path)
        self.proxymodel.setup_filter(self.root_path, [])
        self.setRootIndex(self.proxymodel.mapFromSource(index))

    def get_index(self, filename):
        """
        Return index associated with filename.

        Parameters
        ----------
        filename: str
            String with the filename.
        """
        index = self.fsmodel.index(filename)
        if index.isValid() and index.model() is self.fsmodel:
            return self.proxymodel.mapFromSource(index)

    def set_folder_names(self, folder_names):
        """
        Set folder names

        Parameters
        ----------
        folder_names: list
            List with the folder names.
        """
        assert self.root_path is not None
        path_list = [osp.join(self.root_path, dirname)
                     for dirname in folder_names]
        self.proxymodel.setup_filter(self.root_path, path_list)

    def get_filename(self, index):
        """
        Return filename from index

        Parameters
        ----------
        index: int
            Index of the list of filenames
        """
        if index:
            path = self.fsmodel.filePath(self.proxymodel.mapToSource(index))
            return osp.normpath(str(path))

    def setup_project_view(self):
        """Setup view for projects."""
        for i in [1, 2, 3]:
            self.hideColumn(i)
        self.setHeaderHidden(True)

    # ---- Events
    def directory_clicked(self, dirname, index):
        if index and index.isValid():
            if self.get_conf('single_click_to_open'):
                state = not self.isExpanded(index)
            else:
                state = self.isExpanded(index)
            self.setExpanded(index, state)


class ProjectExplorerTreeWidget(FilteredDirView):
    """Explorer tree widget"""

    sig_delete_project = Signal()

    def __init__(self, parent, show_hscrollbar=True):
        FilteredDirView.__init__(self, parent)
        self.last_folder = None
        self.setSelectionMode(FilteredDirView.ExtendedSelection)
        self.show_hscrollbar = show_hscrollbar

        # Enable drag & drop events
        self.setDragEnabled(True)
        self.setDragDropMode(FilteredDirView.DragDrop)

    # ------Public API---------------------------------------------------------
    @Slot(bool)
    def toggle_hscrollbar(self, checked):
        """Toggle horizontal scrollbar"""
        self.set_conf('show_hscrollbar', checked)
        self.show_hscrollbar = checked
        self.header().setStretchLastSection(not checked)
        self.header().setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.header().setSectionResizeMode(QHeaderView.ResizeToContents)

    # ---- Internal drag & drop
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

        # QTreeView must not remove the source items even in MoveAction mode:
        # event.setDropAction(Qt.CopyAction)

        dst = self.get_filename(self.indexAt(event.pos()))
        yes_to_all, no_to_all = None, None
        src_list = [to_text_string(url.toString())
                    for url in event.mimeData().urls()]
        if len(src_list) > 1:
            buttons = (QMessageBox.Yes | QMessageBox.YesToAll |
                       QMessageBox.No | QMessageBox.NoToAll |
                       QMessageBox.Cancel)
        else:
            buttons = QMessageBox.Yes | QMessageBox.No
        for src in src_list:
            if src == dst:
                continue
            dst_fname = osp.join(dst, osp.basename(src))
            if osp.exists(dst_fname):
                if yes_to_all is not None or no_to_all is not None:
                    if no_to_all:
                        continue
                elif osp.isfile(dst_fname):
                    answer = QMessageBox.warning(
                        self,
                        _('Project explorer'),
                        _('File <b>%s</b> already exists.<br>'
                          'Do you want to overwrite it?') % dst_fname,
                        buttons
                    )

                    if answer == QMessageBox.No:
                        continue
                    elif answer == QMessageBox.Cancel:
                        break
                    elif answer == QMessageBox.YesToAll:
                        yes_to_all = True
                    elif answer == QMessageBox.NoToAll:
                        no_to_all = True
                        continue
                else:
                    QMessageBox.critical(
                        self,
                        _('Project explorer'),
                        _('Folder <b>%s</b> already exists.') % dst_fname,
                        QMessageBox.Ok
                    )
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
                QMessageBox.critical(
                    self,
                    _("Project Explorer"),
                    _("<b>Unable to %s <i>%s</i></b>"
                      "<br><br>Error message:<br>%s") % (action_str, src,
                                                         str(error))
                )

    @Slot()
    def delete(self, fnames=None):
        """Delete files"""
        if fnames is None:
            fnames = self.get_selected_filenames()
        multiple = len(fnames) > 1
        yes_to_all = None
        for fname in fnames:
            if fname == self.proxymodel.path_list[0]:
                self.sig_delete_project.emit()
            else:
                yes_to_all = self.delete_file(fname, multiple, yes_to_all)
                if yes_to_all is not None and not yes_to_all:
                    # Canceled
                    break

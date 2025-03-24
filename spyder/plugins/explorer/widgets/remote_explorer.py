import logging
import os
from datetime import datetime

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QStandardItem, QStandardItemModel
from qtpy.QtWidgets import QTreeView, QVBoxLayout, QWidget

from spyder.utils.icon_manager import ima

logger = logging.getLogger(__name__)


class RemoteExplorer(QWidget):
    sig_dir_opened = Signal(str, str)

    def __init__(self, parent=None, data=None):
        super().__init__(parent=parent)
        self.histindex = None
        self.history = []
        self.root_prefix = ""
        self.server_id = None
        self.tree = QTreeView(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(
            [
                "Name",
                "Size",
                "Type",
                "Created",
                "IsLink",
                "Mode",
                "uid",
                "gid",
                "mtime",
                "ino",
                "nlink",
            ]
        )
        self.tree.header().setDefaultSectionSize(180)
        self.tree.setModel(self.model)
        if data:
            self.import_data(data)
        self.tree.expandAll()
        self.tree.doubleClicked.connect(self._open_item)

    def _open_item(self, index):
        data = self.model.data(index, Qt.UserRole + 1)
        path = data["name"]
        data_type = data["type"]
        if data_type == "directory":
            self.chdir(path, emit=True)

    def import_data(self, data):
        self.model.setRowCount(0)
        root = self.model.invisibleRootItem()
        for item in data:
            path = item["name"]
            name = os.path.relpath(path, self.root_prefix)
            item_type = item["type"]
            icon = ima.icon("FileIcon")
            if item_type == "directory":
                icon = ima.icon("DirClosedIcon")
            base_item = QStandardItem(icon, name)
            base_item.setEditable(False)
            base_item.setData(item)
            root.appendRow(
                [
                    base_item,
                    QStandardItem(str(item["size"])),
                    QStandardItem(item_type),
                    QStandardItem(
                        datetime.fromtimestamp(item["created"]).strftime(
                            "%Y-%m-%d"
                        )
                    ),
                    QStandardItem(str(item["islink"])),
                    QStandardItem(str(item["mode"])),
                    QStandardItem(str(item["uid"])),
                    QStandardItem(str(item["gid"])),
                    QStandardItem(
                        datetime.fromtimestamp(item["mtime"]).strftime(
                            "%Y-%m-%d"
                        )
                    ),
                    QStandardItem(str(item["ino"])),
                    QStandardItem(str(item["nlink"])),
                ]
            )

    def chdir(self, directory=None, server_id=None, emit=True, browsing_history=False):
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
        self.root_prefix = directory
        if server_id:
            self.server_id = server_id
        self.refresh()
        if emit:
            self.sig_dir_opened.emit(directory, self.server_id)

    def set_current_folder(self, folder):
        self.root_prefix = folder
        return self.model.invisibleRootItem()

    def get_current_folder(self):
        return self.root_prefix

    def go_to_parent_directory(self):
        logger.info(f"Go to parent directory: {self.root_prefix}")
        parent_directory = os.path.dirname(self.root_prefix)
        self.chdir(parent_directory)

    def go_to_previous_directory(self):
        logger.info("Go to previous directory")
        self.histindex -= 1
        self.chdir(browsing_history=True)

    def go_to_next_directory(self):
        logger.info("Go to next directory")
        self.histindex += 1
        self.chdir(browsing_history=True)

    def change_filter_state(self):
        pass

    def refresh(self, new_path=None, force_current=False):
        self.previous_action.setEnabled(False)
        self.next_action.setEnabled(False)

        if self.histindex is not None:
            self.previous_action.setEnabled(self.histindex > 0)
            self.next_action.setEnabled(self.histindex < len(self.history) - 1)

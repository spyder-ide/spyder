# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import asyncio
import logging
import os
from datetime import datetime

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QStandardItem, QStandardItemModel
from qtpy.QtWidgets import QTreeView, QVBoxLayout, QWidget

from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.api.translations import _
from spyder.plugins.remoteclient.api.modules.file_services import RemoteOSError
from spyder.utils.icon_manager import ima


logger = logging.getLogger(__name__)


class RemoteExplorer(QWidget):
    sig_dir_opened = Signal(str, str)
    sig_stop_spinner_requested = Signal()

    # TODO: This should come from a config
    INIT_FILES_DISPLAY = 5
    FETCH_FILES = 5
    MAX_FILES_DISPLAY = 5

    def __init__(self, parent=None, data=None):
        super().__init__(parent=parent)
        self.remote_files_manager = None
        self.background_load = set()
        self.files = []
        self.extra_files = []
        self.more_files_available = False
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
        self.tree.doubleClicked.connect(self._clicked_item)

    def _clicked_item(self, index):
        data = self.model.data(index, Qt.UserRole + 1)
        if data:
            data_name = data["name"]
            data_type = data["type"]
            if data_type == "directory":
                self.chdir(data_name, emit=True)
            elif data_type == "ACTION" and data_name == "FETCH_MORE":
                self.fetch_more_files()

    def import_data(self, data, reset=True):
        if reset:
            self.model.setRowCount(0)
        root = self.model.invisibleRootItem()

        more_files_items = self.model.match(self.model.index(0, 0), Qt.DisplayRole, _("Show more files"))
        if len(more_files_items):
            # Remove more files item
            self.model.removeRow(more_files_items[-1].row())

        more_files_available = self.model.match(self.model.index(0, 0), Qt.DisplayRole, _("Maximum number of files to display reached!"))
        if len(more_files_available):
            # Remove more items available
            self.model.removeRow(more_files_available[-1].row())

        for item in data:
            path = item["name"]
            name = os.path.relpath(path, self.root_prefix)
            item_type = item["type"]
            icon = ima.icon("FileIcon")
            if item_type == "directory":
                icon = ima.icon("DirClosedIcon")
            name_item = QStandardItem(icon, name)
            name_item.setData(item)
            size_item = QStandardItem(str(item["size"]))
            type_item = QStandardItem(item_type)
            created_item = QStandardItem(
                datetime.fromtimestamp(item["created"]).strftime(
                    "%Y-%m-%d"
                )
            )
            islink_item = QStandardItem(str(item["islink"]))
            mode_item = QStandardItem(str(item["mode"]))
            uid_item = QStandardItem(str(item["uid"]))
            gid_item = QStandardItem(str(item["gid"]))
            mtime_item = QStandardItem(
                datetime.fromtimestamp(item["mtime"]).strftime(
                    "%Y-%m-%d"
                )
            )
            ino_item = QStandardItem(str(item["ino"]))
            nlink_item = QStandardItem(str(item["nlink"]))
            items = [
                name_item,
                size_item,
                type_item,
                created_item,
                islink_item,
                mode_item,
                uid_item,
                gid_item,
                mtime_item,
                ino_item,
                nlink_item,
            ]
            for standard_item in items:
                standard_item.setEditable(False)
            root.appendRow(items)

        if len(self.extra_files):
            fetch_more_item = QStandardItem(_("Show more files"))
            fetch_more_item.setEditable(False)
            fetch_more_item.setData({"name": "FETCH_MORE", "type": "ACTION"})
            root.appendRow(fetch_more_item)
            self.tree.setFirstColumnSpanned(fetch_more_item.index().row(), root.index(), True)
        elif len(self.extra_files) == 0 and self.more_files_available:
            more_items_avaialable = QStandardItem(_("Maximum number of files to display reached!"))
            more_items_avaialable.setEditable(False)
            root.appendRow(more_items_avaialable)
            self.tree.setFirstColumnSpanned(more_items_avaialable.index().row(), root.index(), True)

    @AsyncDispatcher.QtSlot
    def _on_remote_ls(self, future):
        data = future.result()
        logger.info(data)
        self.import_data(data)

    @AsyncDispatcher(loop="explorer")
    async def _do_remote_ls(self, path, server_id):
        if not self.remote_files_manager:
            return
        try:
            generator = self.remote_files_manager.ls(path)
            self.files = []
            async for file in generator:
                if len(self.files) <= self.INIT_FILES_DISPLAY:
                    self.files.append(file)
                    continue
                break
            if len(self.files) > self.INIT_FILES_DISPLAY:
                task = asyncio.create_task(self._extra_files(generator))
                self.background_load.add(task)
                task.add_done_callback(self.background_load.discard)
            else:
                for task in self.background_load:
                    task.cancel()
                self.extra_files = []
                self.more_files_available = False
            return self.files
        except RemoteOSError as error:
            logger.info(error)

    async def _extra_files(self, generator):
        self.extra_files = []
        self.more_files_available = False
        async for file in generator:
            self.extra_files.append(file)
            if len(self.extra_files) + len(self.files) >= self.MAX_FILES_DISPLAY:
                self.more_files_available = True
                break
        logger.info("extra_files")
        logger.info(self.extra_files)

    def chdir(self, directory=None, server_id=None, emit=True, browsing_history=False, remote_files_manager=None):
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
        if remote_files_manager:
            self.remote_files_manager = remote_files_manager
        self.refresh(force_current=True)
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
        # TODO: Handle filter button and update view to only should required files
        pass

    def fetch_more_files(self):
        new_files = self.extra_files[:self.FETCH_FILES]
        del self.extra_files[:self.FETCH_FILES]
        self.import_data(new_files, reset=False)
        logger.info("New extra_files")
        logger.info(self.extra_files)

    def refresh(self, new_path=None, force_current=False):
        if force_current:
            if new_path is None:
                new_path = self.root_prefix
            self._do_remote_ls(new_path, self.server_id).connect(self._on_remote_ls)

        self.previous_action.setEnabled(False)
        self.next_action.setEnabled(False)

        if self.histindex is not None:
            self.previous_action.setEnabled(self.histindex > 0)
            self.next_action.setEnabled(self.histindex < len(self.history) - 1)
        self.sig_stop_spinner_requested.emit()

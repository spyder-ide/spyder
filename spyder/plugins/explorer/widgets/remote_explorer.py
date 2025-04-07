# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import asyncio
import fnmatch
import logging
import os
from datetime import datetime

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QStandardItem, QStandardItemModel
from qtpy.QtWidgets import QTreeView, QVBoxLayout, QWidget

from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import _
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.plugins.remoteclient.api.modules.file_services import RemoteOSError
from spyder.utils.icon_manager import ima


logger = logging.getLogger(__name__)


class RemoteExplorer(QWidget, SpyderWidgetMixin):
    sig_dir_opened = Signal(str, str)
    sig_stop_spinner_requested = Signal()

    # TODO: This should come from a config
    INIT_FILES_DISPLAY = 500
    FETCH_FILES = 500
    MAX_FILES_DISPLAY = 2000

    def __init__(self, parent=None, class_parent=None, files=None):
        super().__init__(parent=parent, class_parent=parent)
        self.remote_files_manager = None
        self.background_load = set()
        self.filter_on = False
        self.name_filters = []
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
                "Date Modified",
            ]
        )
        self.tree.header().setDefaultSectionSize(180)
        self.tree.setModel(self.model)
        if files:
            self.set_files(files)
        self.tree.expandAll()
        self.tree.entered.connect(self._on_entered_item)

    @on_conf_change(
        option=[
            "size_column",
            "type_column",
            "date_column",
            "name_filters",
            "show_hidden",
            "single_click_to_open",
        ]
    )
    def on_conf_update(self, option, value):
        if option == "size_column":
            self.tree.setColumnHidden(1, not value)
        elif option == "type_column":
            self.tree.setColumnHidden(2, not value)
        elif option == "date_column":
            self.tree.setColumnHidden(3, not value)
        elif option == "name_filters":
            if self.filter_on:
                self.filter_files(value)
        elif option == "show_hidden":
            self.refresh(force_current=True)
        elif option == "single_click_to_open":
            self.set_single_click_to_open(value)

    def _on_entered_item(self, index):
        if self.get_conf('single_click_to_open'):
            self.tree.setCursor(Qt.PointingHandCursor)
            self.tree.header().setCursor(Qt.ArrowCursor)
        else:
            self.tree.setCursor(Qt.ArrowCursor)

    def _on_clicked_item(self, index):
        data_index = self.model.index(index.row(), 0)
        data = self.model.data(data_index, Qt.UserRole + 1)
        if data:
            data_name = data["name"]
            data_type = data["type"]
            if data_type == "directory":
                self.chdir(data_name, emit=True)
            elif data_type == "ACTION" and data_name == "FETCH_MORE":
                self.fetch_more_files()

    @AsyncDispatcher.QtSlot
    def _on_remote_ls(self, future):
        data = future.result()
        logger.info(data)
        self.set_files(data)

    @AsyncDispatcher(loop="explorer")
    async def _do_remote_ls(self, path, server_id):
        if not self.remote_files_manager:
            return
        try:
            files = []
            generator = self.remote_files_manager.ls(path)
            async for file in generator:
                file_name = os.path.relpath(file["name"], self.root_prefix)
                file_type = file["type"]
                if len(files) <= self.INIT_FILES_DISPLAY:
                    if not self.get_conf(
                        "show_hidden"
                    ) and file_name.startswith("."):
                        continue
                    if (
                        self.name_filters
                        and len(self.name_filters)
                        and file_type == "file"
                    ):
                        for name_filter in self.name_filters:
                            if file_type == "file" and fnmatch.fnmatch(
                                file_name, name_filter
                            ):
                                files.append(file)
                                break
                    else:
                        files.append(file)
                    continue
                break
            if len(files) > self.INIT_FILES_DISPLAY:
                task = asyncio.create_task(self._get_extra_files(generator))
                self.background_load.add(task)
                task.add_done_callback(self.background_load.discard)
            else:
                for task in self.background_load:
                    task.cancel()
                self.extra_files = []
                self.more_files_available = False
            return files
        except RemoteOSError as error:
            logger.info(error)

    async def _get_extra_files(self, generator):
        self.extra_files = []
        self.more_files_available = False
        async for file in generator:
            file_name = os.path.relpath(file["name"], self.root_prefix)
            file_type = file["type"]
            if not self.get_conf("show_hidden") and file_name.startswith("."):
                continue
            if (
                self.name_filters
                and len(self.name_filters)
                and file_type == "file"
            ):
                for name_filter in self.name_filters:
                    if file_type == "file" and fnmatch.fnmatch(
                        file_name, name_filter
                    ):
                        self.extra_files.append(file)
                        break
            else:
                self.extra_files.append(file)
            self.extra_files.append(file)
            if (
                len(self.extra_files) + len(self.model.rowCount())
                >= self.MAX_FILES_DISPLAY
            ):
                self.more_files_available = True
                break
        logger.info("extra_files")
        logger.info(self.extra_files)

    @AsyncDispatcher.QtSlot
    def chdir(
        self,
        directory=None,
        server_id=None,
        emit=True,
        browsing_history=False,
        remote_files_manager=None,
    ):
        if browsing_history:
            directory = self.history[self.histindex]
        elif directory in self.history:
            self.histindex = self.history.index(directory)
        else:
            if self.histindex is None:
                self.history = []
            else:
                self.history = self.history[: self.histindex + 1]
            if len(self.history) == 0 or (
                self.history and self.history[-1] != directory
            ):
                self.history.append(directory)
            self.histindex = len(self.history) - 1
        if directory == self.root_prefix:
            return
        self.root_prefix = directory
        if server_id:
            self.server_id = server_id
        if remote_files_manager:
            self.remote_files_manager = remote_files_manager
        self.refresh(force_current=True)
        if emit:
            self.sig_dir_opened.emit(directory, self.server_id)

    def set_files(self, files, reset=True):
        if reset:
            self.model.setRowCount(0)
        if files:
            root = self.model.invisibleRootItem()

            more_files_items = self.model.match(
                self.model.index(0, 0), Qt.DisplayRole, _("Show more files")
            )
            if len(more_files_items):
                # Remove more files item
                self.model.removeRow(more_files_items[-1].row())

            more_files_available = self.model.match(
                self.model.index(0, 0),
                Qt.DisplayRole,
                _("Maximum number of files to display reached!"),
            )
            if len(more_files_available):
                # Remove more items available item
                self.model.removeRow(more_files_available[-1].row())

            for file in files:
                path = file["name"]
                name = os.path.relpath(path, self.root_prefix)
                file_type = file["type"]
                icon = ima.icon("FileIcon")
                if file_type == "directory":
                    icon = ima.icon("DirClosedIcon")
                file_name = QStandardItem(icon, name)
                file_name.setData(file)
                file_name.setToolTip(file["name"])
                file_size = QStandardItem(str(file["size"]))
                file_type = QStandardItem(file_type)
                file_date_modified = QStandardItem(
                    datetime.fromtimestamp(file["mtime"]).strftime(
                        "%d/%m/%Y %I:%M %p"
                    )
                )
                items = [
                    file_name,
                    file_size,
                    file_type,
                    file_date_modified,
                ]
                for standard_item in items:
                    standard_item.setEditable(False)
                root.appendRow(items)

            if len(self.extra_files):
                fetch_more_item = QStandardItem(_("Show more files"))
                fetch_more_item.setEditable(False)
                fetch_more_item.setData(
                    {"name": "FETCH_MORE", "type": "ACTION"}
                )
                root.appendRow(fetch_more_item)
                self.tree.setFirstColumnSpanned(
                    fetch_more_item.index().row(), root.index(), True
                )
            elif len(self.extra_files) == 0 and self.more_files_available:
                more_items_avaialable = QStandardItem(
                    _("Maximum number of files to display reached!")
                )
                more_items_avaialable.setEditable(False)
                root.appendRow(more_items_avaialable)
                self.tree.setFirstColumnSpanned(
                    more_items_avaialable.index().row(), root.index(), True
                )

    def fetch_more_files(self):
        new_files = self.extra_files[: self.FETCH_FILES]
        del self.extra_files[: self.FETCH_FILES]
        self.set_files(new_files, reset=False)
        logger.info("New extra_files")
        logger.info(self.extra_files)

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

    def refresh(self, new_path=None, force_current=False):
        if force_current:
            if new_path is None:
                new_path = self.root_prefix
            self._do_remote_ls(new_path, self.server_id).connect(
                self._on_remote_ls
            )

        self.previous_action.setEnabled(False)
        self.next_action.setEnabled(False)

        if self.histindex is not None:
            self.previous_action.setEnabled(self.histindex > 0)
            self.next_action.setEnabled(self.histindex < len(self.history) - 1)
        self.sig_stop_spinner_requested.emit()

    def set_single_click_to_open(self, value):
        if value:
            try:
                self.tree.doubleClicked.disconnect(self._on_clicked_item)
            except TypeError:
                pass
            self.tree.clicked.connect(self._on_clicked_item)
        else:
            try:
                self.tree.clicked.disconnect(self._on_clicked_item)
            except TypeError:
                pass
            self.tree.doubleClicked.connect(self._on_clicked_item)

    def filter_files(self, name_filters=None):
        """Filter files given the defined list of filters."""
        if name_filters is None:
            name_filters = self.get_conf("name_filters")
        self.name_filters = []
        if self.filter_on:
            self.name_filters = name_filters
        self.refresh(force_current=True)

    def change_filter_state(self):
        self.filter_on = not self.filter_on
        self.filter_button.setChecked(self.filter_on)
        self.filter_button.setToolTip(_("Filter filenames"))
        self.filter_files()

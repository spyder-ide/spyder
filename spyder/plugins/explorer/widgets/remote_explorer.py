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

from qtpy.QtCore import QSortFilterProxyModel, Qt, Signal
from qtpy.QtGui import QStandardItem, QStandardItemModel
from qtpy.QtWidgets import QTreeView, QVBoxLayout, QWidget

from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import _
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.plugins.remoteclient.api.modules.base import (
    SpyderRemoteSessionClosed,
)
from spyder.plugins.remoteclient.api.modules.file_services import RemoteOSError
from spyder.utils.icon_manager import ima


logger = logging.getLogger(__name__)


class RemoteQSortFilterProxyModel(QSortFilterProxyModel):

    def lessThan(self, left, right):
        right_data = self.sourceModel().data(
            self.sourceModel().index(right.row(), 0), Qt.UserRole + 1
        )
        if right_data["type"] == "ACTION":
            return self.sortOrder() == Qt.AscendingOrder

        left_data = self.sourceModel().data(
            self.sourceModel().index(left.row(), 0), Qt.UserRole + 1
        )
        if left_data["type"] == "ACTION":
            return self.sortOrder() == Qt.DescendingOrder

        if left_data["type"] == "directory" and right_data["type"] == "file":
            return True

        if left_data["type"] == "file" and right_data["type"] == "directory":
            return False

        return super().lessThan(left, right)


class RemoteExplorer(QWidget, SpyderWidgetMixin):
    sig_dir_opened = Signal(str, str)
    sig_stop_spinner_requested = Signal()

    def __init__(self, parent=None, class_parent=None, files=None):
        super().__init__(parent=parent, class_parent=parent)

        # General attributes
        self.remote_files_manager = None
        self.server_id = None
        self.root_prefix = ""

        self.background_files_load = set()
        self.extra_files = []
        self.more_files_available = False

        self.filter_on = False
        self.name_filters = []

        self.history = []
        self.histindex = None

        # Model and widget setup
        self.model = QStandardItemModel(self)
        self.model.setHorizontalHeaderLabels(
            [
                "Name",
                "Size",
                "Type",
                "Date Modified",
            ]
        )
        self.proxy_model = RemoteQSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.model)

        self.view = QTreeView(self)
        self.view.setModel(self.proxy_model)
        self.view.setSortingEnabled(True)

        if files:
            self.set_files(files)

        self.view.sortByColumn(0, Qt.AscendingOrder)
        self.view.entered.connect(self._on_entered_item)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

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
            self.view.setColumnHidden(1, not value)
        elif option == "type_column":
            self.view.setColumnHidden(2, not value)
        elif option == "date_column":
            self.view.setColumnHidden(3, not value)
        elif option == "name_filters":
            if self.filter_on:
                self.filter_files(value)
        elif option == "show_hidden":
            self.refresh(force_current=True)
        elif option == "single_click_to_open":
            self.set_single_click_to_open(value)

    def _on_entered_item(self, index):
        if self.get_conf("single_click_to_open"):
            self.view.setCursor(Qt.PointingHandCursor)
            self.view.header().setCursor(Qt.ArrowCursor)
        else:
            self.view.setCursor(Qt.ArrowCursor)

    def _on_clicked_item(self, index):
        source_index = self.proxy_model.mapToSource(index)
        data_index = self.model.index(source_index.row(), 0)
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
        self.set_files(data)

    @AsyncDispatcher(loop="explorer")
    async def _do_remote_ls(self, path, server_id):
        if not self.remote_files_manager:
            return

        for task in self.background_files_load:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self.extra_files = []
        self.more_files_available = False
        files = []
        try:
            init_files_display = self.get_conf("init_files_display")
            generator = self.remote_files_manager.ls(path)
            async for file in generator:
                file_name = os.path.relpath(file["name"], self.root_prefix)
                file_type = file["type"]
                if len(files) < init_files_display:
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
                else:
                    break

            if len(files) == init_files_display:
                task = asyncio.create_task(
                    self._get_extra_files(generator, len(files))
                )
                self.background_files_load.add(task)
                task.add_done_callback(self.background_files_load.discard)

        except RemoteOSError as error:
            # TODO: Should the error be shown in some way?
            logger.error(error)
        except SpyderRemoteSessionClosed:
            self.remote_files_manager = None

        return files

    async def _get_extra_files(self, generator, already_added):
        self.extra_files = []
        self.more_files_available = False
        async for file in generator:
            if len(self.extra_files) + already_added == self.get_conf(
                "max_files_display"
            ):
                self.more_files_available = True
                break

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

        logger.debug(
            f"{len(self.extra_files)} available extra files to be shown"
        )

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
            logger.debug(f"Setting {len(files)} files")
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

            # Add fetch more or more items available item
            if len(self.extra_files):
                fetch_more_item = QStandardItem(_("Show more files"))
                fetch_more_item.setEditable(False)
                fetch_more_item.setData(
                    {"name": "FETCH_MORE", "type": "ACTION"}
                )
                root.appendRow(fetch_more_item)
                self.view.setFirstColumnSpanned(
                    fetch_more_item.index().row(), root.index(), True
                )
            elif len(self.extra_files) == 0 and self.more_files_available:
                more_items_available = QStandardItem(
                    _("Maximum number of files to display reached!")
                )
                more_items_available.setEditable(False)
                more_items_available.setData(
                    {"name": "MESSAGE", "type": "ACTION"}
                )
                root.appendRow(more_items_available)
                self.view.setFirstColumnSpanned(
                    more_items_available.index().row(), root.index(), True
                )

            self.view.resizeColumnToContents(0)

    def fetch_more_files(self):
        fetch_files_display = self.get_conf("fetch_files_display")
        new_files = self.extra_files[:fetch_files_display]
        del self.extra_files[:fetch_files_display]
        self.set_files(new_files, reset=False)
        logger.debug(
            f"{len(self.extra_files)} extra files remaining to be shown"
        )

    def set_current_folder(self, folder):
        self.root_prefix = folder
        return self.model.invisibleRootItem()

    def get_current_folder(self):
        return self.root_prefix

    def go_to_parent_directory(self):
        parent_directory = os.path.dirname(self.root_prefix)
        logger.debug(
            f"Going to parent directory of {self.root_prefix}: "
            f"{parent_directory}"
        )
        self.chdir(parent_directory)

    def go_to_previous_directory(self):
        self.histindex -= 1
        logger.debug(
            f"Going to previous directory in history with index "
            f"{self.histindex}"
        )
        self.chdir(browsing_history=True)

    def go_to_next_directory(self):
        self.histindex += 1
        logger.debug(
            f"Going to next directory in history with index {self.histindex}"
        )
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
                self.view.doubleClicked.disconnect(self._on_clicked_item)
            except TypeError:
                pass
            self.view.clicked.connect(self._on_clicked_item)
        else:
            try:
                self.view.clicked.disconnect(self._on_clicked_item)
            except TypeError:
                pass
            self.view.doubleClicked.connect(self._on_clicked_item)

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

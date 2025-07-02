# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import asyncio
import fnmatch
import io
import logging
import os
import posixpath
from datetime import datetime

from qtpy.compat import getopenfilename, getsavefilename
from qtpy.QtCore import QSortFilterProxyModel, Qt, Signal
from qtpy.QtGui import QClipboard, QStandardItem, QStandardItemModel
from qtpy.QtWidgets import (
    QApplication,
    QInputDialog,
    QMessageBox,
    QLineEdit,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import _
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.config.base import get_conf_path
from spyder.plugins.editor.utils.editor import get_default_file_content
from spyder.plugins.remoteclient.api.modules.base import (
    SpyderRemoteSessionClosed,
)
from spyder.plugins.remoteclient.api.modules.file_services import (
    RemoteFileServicesError,
    RemoteOSError,
)
from spyder.utils.icon_manager import ima
from spyder.utils.misc import getcwd_or_home


logger = logging.getLogger(__name__)


class RemoteViewMenus:
    Context = "remote_context_menu"
    New = "remote_new_menu"


class RemoteViewNewSubMenuSections:
    General = 'remote_general_section'
    Language = 'remote_language_section'


class RemoteExplorerActions:
    CopyPaste = "remote_copy_paste_action"
    CopyPath = "remote_copy_path_action"
    Delete = "remote_delete_action"
    Download = "remote_download_action"
    NewDirectory = "remote_new_directory_action"
    NewFile = "remote_new_file_action"
    NewModule = "remote_new_module_action"
    NewPackage = "remote_new_package_action"
    Rename = "remote_rename_action"
    Upload = "remote_upload_file_action"


class RemoteExplorerContextMenuSections:
    CopyPaste = "remote_copy_paste_section"
    Extras = "remote_extras_section"
    New = "remote_new_section"


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
    sig_start_spinner_requested = Signal()
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

        # Model, actions and widget setup
        self.context_menu = self.create_menu(RemoteViewMenus.Context)
        new_submenu = self.create_menu(
            RemoteViewMenus.New,
            _('New'),
        )

        self.new_package_action = self.create_action(
            RemoteExplorerActions.NewPackage,
            text=_("Python package..."),
            icon=self.create_icon('package_new'),
            triggered=self.new_package,
        )
        self.new_module_action = self.create_action(
            RemoteExplorerActions.NewModule,
            text=_("Python file..."),
            icon=self.create_icon('python'),
            triggered=self.new_module,
        )
        self.new_directory_action = self.create_action(
            RemoteExplorerActions.NewDirectory,
            text=_("Folder..."),
            icon=self.create_icon('folder_new'),
            triggered=self.new_directory,
        )
        self.new_file_action = self.create_action(
            RemoteExplorerActions.NewFile,
            text=_("File..."),
            icon=self.create_icon('TextFileIcon'),
            triggered=self.new_file,
        )
        self.copy_paste_action = self.create_action(
            RemoteExplorerActions.CopyPaste,
            _("Copy and Paste..."),
            icon=self.create_icon("editcopy"),
            triggered=self.copy_paste_item,
        )
        self.rename_action = self.create_action(
            RemoteExplorerActions.Rename,
            _("Rename..."),
            icon=self.create_icon("rename"),
            triggered=self.rename_item,
        )
        self.copy_path_action = self.create_action(
            RemoteExplorerActions.CopyPath,
            _("Copy path"),
            triggered=self.copy_path,
        )
        self.delete_action = self.create_action(
            RemoteExplorerActions.Delete,
            _("Delete..."),
            icon=self.create_icon("editclear"),
            triggered=self.delete_item,
        )
        self.download_action = self.create_action(
            RemoteExplorerActions.Download,
            _("Download..."),
            icon=self.create_icon("fileimport"),
            triggered=self.download_item,
        )
        self.upload_file_action = self.create_action(
            RemoteExplorerActions.Upload,
            _("Upload file"),
            icon=self.create_icon("fileexport"),
            triggered=self.upload_file,
        )

        for item in [self.new_file_action, self.new_directory_action]:
            self.add_item_to_menu(
                item,
                new_submenu,
                section=RemoteViewNewSubMenuSections.General,
            )

        for item in [self.new_module_action, self.new_package_action]:
            self.add_item_to_menu(
                item,
                new_submenu,
                section=RemoteViewNewSubMenuSections.Language,
            )

        for item in [
            new_submenu,
            self.rename_action,
            self.delete_action,
        ]:
            self.add_item_to_menu(
                item,
                self.context_menu,
                section=RemoteExplorerContextMenuSections.New,
            )

        for item in [
            self.copy_paste_action,
            self.copy_path_action,
        ]:
            self.add_item_to_menu(
                item,
                self.context_menu,
                section=RemoteExplorerContextMenuSections.CopyPaste,
            )

        for item in [self.download_action]:
            self.add_item_to_menu(
                item,
                self.context_menu,
                section=RemoteExplorerContextMenuSections.Extras,
            )

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_show_context_menu)

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
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(
            self._on_show_context_menu
        )

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

    def _on_show_context_menu(self, position):
        index = self.view.indexAt(position)
        if not index.isValid():
            self.view.setCurrentIndex(index)
            self.view.clearSelection()
            data = {}
            data_available = False
            is_file = False
        else:
            source_index = self.proxy_model.mapToSource(
                self.view.currentIndex()
            )
            data_index = self.model.index(source_index.row(), 0)
            data = self.model.data(data_index, Qt.UserRole + 1)
            data_available = bool(data)
            is_file = (
                data_available and data.get("type", "directory") == "file"
            )

        # Disable actions that require a valid selection
        self.rename_action.setEnabled(data_available)
        self.delete_action.setEnabled(data_available)

        # Disable actions not suitable for directories
        self.copy_paste_action.setEnabled(is_file)

        global_position = self.mapToGlobal(position)
        self.context_menu.popup(global_position)

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

    def _handle_future_response_error(self, future, error_title, error_message):
        try:
            # Need to call `future.result()` to get any possible exception
            # generated over the remote server.
            future.result()
        except (RemoteOSError, OSError) as error:
            error_message = f"{error_message}<br><br>{error.message}"
            QMessageBox.critical(self, error_title, error_message)
            logger.error(error)

    @AsyncDispatcher.QtSlot
    def _on_remote_new_package(self, future, package_name):
        self._handle_future_response_error(
            future,
            _("New Python Package error"),
            _("An error occured while trying to create a new Python package"),
        )
        new_name = posixpath.join(package_name, "__init__.py")
        self._new_item(new_name, for_file=True, with_content=True)

    @AsyncDispatcher.QtSlot
    def _on_remote_new_module(self, future):
        self._handle_future_response_error(
            future,
            _("New Python File error"),
            _("An error occured while trying to create a new Python file"),
        )
        self.refresh(force_current=True)

    @AsyncDispatcher(loop="explorer")
    async def _do_remote_new_module(self, new_path, file_content):
        if not self.remote_files_manager:
            self.sig_stop_spinner_requested.emit()
            return

        file_manager = await self.remote_files_manager.open(new_path, mode="w")
        remote_file_response = await file_manager.write(file_content)
        await file_manager.close()

        return remote_file_response

    @AsyncDispatcher.QtSlot
    def _on_remote_new(self, future):
        self._handle_future_response_error(
            future,
            _("New error"),
            _("An error occured while trying to create a file/directory"),
        )
        self.refresh(force_current=True)

    @AsyncDispatcher(loop="explorer")
    async def _do_remote_new(
        self, new_path, for_file=False
    ):
        if not self.remote_files_manager:
            self.sig_stop_spinner_requested.emit()
            return

        if for_file:
            response = await self.remote_files_manager.touch(new_path)
        else:
            response = await self.remote_files_manager.mkdir(new_path)

        return response

    @AsyncDispatcher.QtSlot
    def _on_remote_copy_paste(self, future):
        self._handle_future_response_error(
            future,
            _("Copy and Paste error"),
            _(
                "An error occured while trying to copy and paste a "
                "file/directory"
            ),
        )
        self.refresh(force_current=True)

    @AsyncDispatcher(loop="explorer")
    async def _do_remote_copy_paste(self, old_path, new_path):
        if not self.remote_files_manager:
            self.sig_stop_spinner_requested.emit()
            return

        return await self.remote_files_manager.copy(old_path, new_path)

    @AsyncDispatcher.QtSlot
    def _on_remote_rename(self, future):
        self._handle_future_response_error(
            future,
            _("Rename error"),
            _("An error occured while trying to rename a file"),
        )
        self.refresh(force_current=True)

    @AsyncDispatcher(loop="explorer")
    async def _do_remote_rename(self, old_path, new_path):
        if not self.remote_files_manager:
            self.sig_stop_spinner_requested.emit()
            return

        return await self.remote_files_manager.replace(old_path, new_path)

    @AsyncDispatcher.QtSlot
    def _on_remote_delete(self, future):
        self._handle_future_response_error(
            future,
            _("Delete error"),
            _("An error occured while trying to delete a file/directory"),
        )
        self.refresh(force_current=True)

    @AsyncDispatcher(loop="explorer")
    async def _do_remote_delete(self, path, is_file=False):
        if not self.remote_files_manager:
            self.sig_stop_spinner_requested.emit()
            return

        if is_file:
            response = await self.remote_files_manager.unlink(path)
        else:
            response = await self.remote_files_manager.rmdir(
                path, non_empty=True
            )

        return response

    @AsyncDispatcher.QtSlot
    def _on_remote_download_file(self, future, remote_filename):
        data = future.result()
        filename, __ = getsavefilename(
            self,
            _("Download file"),
            os.path.join(getcwd_or_home(), remote_filename),
            _("All files") + " (*)",
        )
        if filename:
            try:
                with open(filename, "w") as download_file:
                    download_file.write(data)
            except TypeError:
                with open(filename, "wb") as download_file:
                    download_file.write(data)

        self.sig_stop_spinner_requested.emit()

    @AsyncDispatcher(loop="explorer")
    async def _do_remote_download_directory(self, path):
        if not self.remote_files_manager:
            self.sig_stop_spinner_requested.emit()
            return

        try:
            zip_generator = self.remote_files_manager.zip_directory(path)
            zip_data = io.BytesIO()
            async for data in zip_generator:
                zip_data.write(data)
            zip_data.seek(0)
        except RemoteFileServicesError as download_error:
            error_message = _(
                "An error occured while trying to download {path}".format(
                    path=path
                )
            )
            QMessageBox.critical(self, _("Download error"), error_message)
            logger.debug(f"Unable to download {path}")
            logger.error(
                f"Error while trying to download directory (compressed): "
                f"{download_error.message}"
            )

        return zip_data.getbuffer()

    @AsyncDispatcher(loop="explorer")
    async def _do_remote_download_file(self, path):
        if not self.remote_files_manager:
            self.sig_stop_spinner_requested.emit()
            return

        try:
            file_manager = await self.remote_files_manager.open(path, mode="r")
            file_data = ""
            async for data in file_manager:
                file_data += data
        except RemoteFileServicesError:
            try:
                file_manager = await self.remote_files_manager.open(
                    path, mode="rb"
                )
                file_data = b""
                async for data in file_manager:
                    file_data += data
            except RemoteFileServicesError as download_error:
                error_message = _(
                    "An error occured while trying to download {path}".format(
                        path=path
                    )
                )
                QMessageBox.critical(self, _("Download error"), error_message)
                logger.debug(f"Unable to download {path}")
                logger.error(
                    f"Error while trying to download file: "
                    f"{download_error.message}"
                )

        await file_manager.close()
        return file_data

    @AsyncDispatcher.QtSlot
    def _on_remote_upload_file(self, future):
        self._handle_future_response_error(
            future,
            _("Upload error"),
            _("An error occured while trying to upload a file"),
        )
        self.refresh(force_current=True)

    @AsyncDispatcher(loop="explorer")
    async def _do_remote_upload_file(self, local_path):
        if not self.remote_files_manager:
            self.sig_stop_spinner_requested.emit()
            return

        remote_file = posixpath.join(
            self.root_prefix, os.path.basename(local_path)
        )
        file_content = None

        try:
            with open(local_path, mode="r") as local_file:
                file_content = local_file.read()
            file_manager = await self.remote_files_manager.open(
                remote_file, mode="w"
            )
        except UnicodeDecodeError:
            with open(local_path, mode="rb") as local_file:
                file_content = local_file.read()
            file_manager = await self.remote_files_manager.open(
                remote_file, mode="wb"
            )

        if file_content:
            remote_file_response = await file_manager.write(file_content)

        await file_manager.close()
        return remote_file_response

    @AsyncDispatcher.QtSlot
    def _on_remote_ls(self, future):
        data = future.result()
        self.set_files(data)

    @AsyncDispatcher(loop="explorer")
    async def _do_remote_ls(self, path, server_id):
        if not self.remote_files_manager:
            self.sig_stop_spinner_requested.emit()
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

    def _new_item(self, new_name, for_file=False, with_content=False):
        new_path = posixpath.join(self.root_prefix, new_name)
        if not with_content:
            self._do_remote_new(new_path, for_file=for_file).connect(
                self._on_remote_new
            )
        elif for_file and with_content:
            file_content, __, __ = get_default_file_content(
                get_conf_path("template.py")
            )
            self._do_remote_new_module(new_path, file_content).connect(
                self._on_remote_new_module
            )
        elif not for_file and with_content:

            @AsyncDispatcher.QtSlot
            def remote_package(future):
                self._on_remote_new_package(future, new_name)

            self._do_remote_new(new_path).connect(remote_package)

        self.sig_start_spinner_requested.emit()

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

    def new_package(self):
        new_name, valid = QInputDialog.getText(
            self, _("New Python Package"), _("Name as:"), QLineEdit.Normal, ""
        )
        if valid:
            self._new_item(new_name, with_content=True)

    def new_module(self):
        new_name, valid = QInputDialog.getText(
            self, _("New Python File"), _("Name as:"), QLineEdit.Normal, ".py"
        )
        if valid:
            self._new_item(new_name, for_file=True, with_content=True)

    def new_directory(self):
        new_name, valid = QInputDialog.getText(
            self, _("New Folder"), _("Name as:"), QLineEdit.Normal, ""
        )
        if valid:
            self._new_item(new_name)

    def new_file(self):
        new_name, valid = QInputDialog.getText(
            self, _("New File"), _("Name as:"), QLineEdit.Normal, ""
        )
        if valid:
            self._new_item(new_name, for_file=True)

    def copy_paste_item(self):
        if (
            not self.view.currentIndex()
            or not self.view.currentIndex().isValid()
        ):
            return

        source_index = self.proxy_model.mapToSource(self.view.currentIndex())
        data_index = self.model.index(source_index.row(), 0)
        data = self.model.data(data_index, Qt.UserRole + 1)
        if data:
            old_path = data["name"]
            relpath = os.path.relpath(old_path, self.root_prefix)
            new_relpath, valid = QInputDialog.getText(
                self,
                _("Copy and Paste"),
                _("Paste as:"),
                QLineEdit.Normal,
                relpath,
            )
            if valid:
                new_path = posixpath.join(self.root_prefix, new_relpath)
                self._do_remote_copy_paste(old_path, new_path).connect(
                    self._on_remote_copy_paste
                )
                self.sig_start_spinner_requested.emit()

    def rename_item(self):
        if (
            not self.view.currentIndex()
            or not self.view.currentIndex().isValid()
        ):
            return

        source_index = self.proxy_model.mapToSource(self.view.currentIndex())
        data_index = self.model.index(source_index.row(), 0)
        data = self.model.data(data_index, Qt.UserRole + 1)
        if data:
            old_path = data["name"]
            relpath = os.path.relpath(old_path, self.root_prefix)
            new_relpath, valid = QInputDialog.getText(
                self, _("Rename"), _("New name:"), QLineEdit.Normal, relpath
            )
            if valid:
                new_path = posixpath.join(self.root_prefix, new_relpath)
                self._do_remote_rename(old_path, str(new_path)).connect(
                    self._on_remote_rename
                )
                self.sig_start_spinner_requested.emit()

    def copy_path(self):
        if (
            not self.view.currentIndex()
            or not self.view.currentIndex().isValid()
        ):
            path = self.root_prefix
        else:
            source_index = self.proxy_model.mapToSource(
                self.view.currentIndex()
            )
            data_index = self.model.index(source_index.row(), 0)
            data = self.model.data(data_index, Qt.UserRole + 1)
            if data:
                path = data["name"]

        cb = QApplication.clipboard()
        cb.setText(path, mode=QClipboard.Mode.Clipboard)

    def delete_item(self):
        if (
            not self.view.currentIndex()
            or not self.view.currentIndex().isValid()
        ):
            return

        source_index = self.proxy_model.mapToSource(self.view.currentIndex())
        data_index = self.model.index(source_index.row(), 0)
        data = self.model.data(data_index, Qt.UserRole + 1)
        if data:
            path = data["name"]
            filename = os.path.relpath(path, self.root_prefix)
            result = QMessageBox.warning(
                self,
                _("Delete"),
                _("Do you really want to delete <b>{filename}</b>?").format(
                    filename=filename
                ),
                QMessageBox.Yes | QMessageBox.No,
            )
            if result == QMessageBox.Yes:
                is_file = data["type"] == "file"
                self._do_remote_delete(path, is_file=is_file).connect(
                    self._on_remote_delete
                )
                self.sig_start_spinner_requested.emit()

    def download_item(self):
        if (
            not self.view.currentIndex()
            or not self.view.currentIndex().isValid()
        ):
            return

        source_index = self.proxy_model.mapToSource(self.view.currentIndex())
        data_index = self.model.index(source_index.row(), 0)
        data = self.model.data(data_index, Qt.UserRole + 1)
        if data:
            path = data["name"]
            filename = os.path.relpath(path, self.root_prefix)
            is_file = data["type"] == "file"
            remote_filename = filename if is_file else f"{filename}.zip"

            @AsyncDispatcher.QtSlot
            def remote_download_file(future):
                self._on_remote_download_file(future, remote_filename)

            if is_file:
                self._do_remote_download_file(path).connect(
                    remote_download_file
                )
            else:
                self._do_remote_download_directory(path).connect(
                    remote_download_file
                )

            self.sig_start_spinner_requested.emit()

    def upload_file(self):
        local_path, __ = getopenfilename(
            self,
            _("Upload file"),
            getcwd_or_home(),
            _("All files") + " (*)",
        )
        if os.path.exists(local_path):
            self._do_remote_upload_file(local_path).connect(
                self._on_remote_upload_file
            )
            self.sig_start_spinner_requested.emit()

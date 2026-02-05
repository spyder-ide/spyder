# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from __future__ import annotations
import asyncio
from enum import Enum
import fnmatch
import functools
import io
import logging
import os
import posixpath
from datetime import datetime

from aiohttp.client_exceptions import ClientResponseError
from qtpy.compat import getexistingdirectory, getopenfilenames
from qtpy.QtCore import QSortFilterProxyModel, Qt, Signal
from qtpy.QtGui import (
    QClipboard,
    QKeySequence,
    QStandardItem,
    QStandardItemModel,
)
from qtpy.QtWidgets import (
    QAbstractItemView,
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
from spyder.config.utils import EDIT_EXTENSIONS
from spyder.plugins.editor.utils.editor import get_default_file_content
from spyder.plugins.remoteclient.api.modules.base import (
    SpyderRemoteSessionClosed,
)
from spyder.plugins.remoteclient.api.protocol import ClientType
from spyder.plugins.remoteclient.api.modules.file_services import (
    RemoteFileServicesError,
    RemoteOSError,
    SpyderRemoteFileServicesAPI,
)
from spyder.plugins.shortcuts.utils import (
    ShortcutData,
    SHORTCUTS_FOR_WIDGETS_DATA,
)
from spyder.utils.icon_manager import ima
from spyder.utils.misc import getcwd_or_home
from spyder.utils.qthelpers import keyevent_to_keysequence_str


logger = logging.getLogger(__name__)


class RemoteViewMenus:
    Context = "remote_context_menu"
    New = "remote_new_menu"


class RemoteViewNewSubMenuSections:
    General = 'remote_general_section'
    Language = 'remote_language_section'


class RemoteExplorerActions:
    Copy = "remote_copy_action"
    Paste = "remote_paste_action"
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


class RemoteExistenceOperations(Enum):
    Upload = "upload"
    Paste = "paste"
    NewFile = "new_file"
    NewFileWithContent = "new_file_with_content"
    NewDirectoryWithContent = "new_directory_with_content"


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
        self.remote_files_manager: SpyderRemoteFileServicesAPI | None = None
        self.server_id: str | None = None
        self.root_prefix: dict[str, str] = {}

        self.background_files_load = set()
        self.extra_files = []
        self.more_files_available = False

        self.filter_on = False
        self.name_filters = []

        self.history = []
        self.histindex = None

        self._files_to_copy: dict[str, list[str]] = {}
        self._files_to_delete: dict[str, int] = {}
        self._files_to_download: dict[str, int] = {}
        self._files_to_paste: dict[str, int] = {}
        self._files_to_rename: dict[str, int] = {}
        self._files_to_upload: dict[str, int] = {}

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
        self.copy_action = self.create_action(
            RemoteExplorerActions.Copy,
            _("Copy"),
            icon=self.create_icon("editcopy"),
            triggered=self.copy_items,
        )
        self.paste_action = self.create_action(
            RemoteExplorerActions.Paste,
            _("Paste"),
            icon=self.create_icon("editpaste"),
            triggered=self.paste_items,
        )
        self.rename_action = self.create_action(
            RemoteExplorerActions.Rename,
            _("Rename..."),
            icon=self.create_icon("rename"),
            triggered=self.rename_items,
        )
        self.copy_path_action = self.create_action(
            RemoteExplorerActions.CopyPath,
            _("Copy absolute path"),
            triggered=self.copy_paths,
        )
        self.delete_action = self.create_action(
            RemoteExplorerActions.Delete,
            _("Delete..."),
            icon=self.create_icon("editclear"),
            triggered=self.delete_items,
        )
        self.download_action = self.create_action(
            RemoteExplorerActions.Download,
            _("Download..."),
            icon=self.create_icon("fileimport"),
            triggered=self.download_items,
        )
        self.upload_file_action = self.create_action(
            RemoteExplorerActions.Upload,
            _("Upload files"),
            icon=self.create_icon("fileexport"),
            triggered=self.upload_files,
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
            self.copy_action,
            self.paste_action,
            self.copy_path_action,
        ]:
            self.add_item_to_menu(
                item,
                self.context_menu,
                section=RemoteExplorerContextMenuSections.CopyPaste,
            )

        for item in [self.upload_file_action, self.download_action]:
            self.add_item_to_menu(
                item,
                self.context_menu,
                section=RemoteExplorerContextMenuSections.Extras,
            )

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_show_context_menu)

        self._register_shortcuts()

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
        self.view.setSelectionMode(QTreeView.ExtendedSelection)
        self.view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
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

    # ---- Private API
    # -------------------------------------------------------------------------
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
        self.copy_action.setEnabled(is_file)
        self.paste_action.setEnabled(
            bool(self._files_to_copy.get(self.server_id, []))
        )

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
            elif (
                data_type == "file"
                and os.path.splitext(data_name)[1] in EDIT_EXTENSIONS
            ):
                QMessageBox.warning(
                    self,
                    _("Unsupported functionality"),
                    _(
                        "Opening remote files in the Editor is not yet "
                        "supported. This feature will be added in Spyder "
                        "6.2.0"
                    )
                )
            elif data_type == "ACTION" and data_name == "FETCH_MORE":
                self.fetch_more_files()

    @property
    def _operation_in_progress(self):
        return (
            self._files_to_delete.get(self.server_id, 0) > 0
            or self._files_to_download.get(self.server_id, 0) > 0
            or self._files_to_paste.get(self.server_id, 0) > 0
            or self._files_to_rename.get(self.server_id, 0) > 0
            or self._files_to_upload.get(self.server_id, 0) > 0
        )

    def _handle_future_response_error(
        self, response, error_title, error_message
    ):
        # Catch errors raised when running async methods.
        # Fixes spyder-ide/spyder#24974
        try:
            response.result()
            return False
        except (RemoteOSError, OSError) as error:
            logger.debug(error)

            if hasattr(error, "message"):
                str_error = error.message
            else:
                str_error = str(error)

            error_message = f"{error_message}<br><br>{str_error}"
            QMessageBox.critical(self, error_title, error_message)
            return True

    @AsyncDispatcher.QtSlot
    def _on_remote_new_package(self, future, package_name):
        error = self._handle_future_response_error(
            future,
            _("New Python Package error"),
            _("An error occured while trying to create a new Python package"),
        )

        if not error:
            # Only create init file if there weren't errors creating its
            # parent.
            new_name = posixpath.join(package_name, "__init__.py")
            self._new_item(new_name, for_file=True, with_content=True)
        else:
            if not self._operation_in_progress:
                self.sig_stop_spinner_requested.emit()

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

        async with await self.remote_files_manager.open(
            new_path, mode="w"
        ) as file_manager:
            return await file_manager.write(file_content)

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
    def _on_remote_paste(self, future):
        self._handle_future_response_error(
            future,
            _("Paste error"),
            _(
                "An error occured while trying to paste a file or directory"
            ),
        )

        if self._files_to_paste[self.server_id] > 0:
            self._files_to_paste[self.server_id] -= 1

        self.refresh(force_current=True)

    @AsyncDispatcher(loop="explorer")
    async def _do_remote_paste(self, old_path, new_path):
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

        if self._files_to_rename[self.server_id] > 0:
            self._files_to_rename[self.server_id] -= 1

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

        if self._files_to_delete[self.server_id] > 0:
            self._files_to_delete[self.server_id] -= 1

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
    def _on_remote_download_file(
        self, future, remote_filename, local_directory, is_file
    ):
        download_error = False
        try:
            data = future.result()
        except (RemoteFileServicesError, ClientResponseError) as error:
            download_error = True
            logger.debug(error)

            if is_file:
                message = _(
                    "An error occurred while trying to download the file "
                    "<b>{}</b> from server <b>{}</b>:"
                    "<br><br>"
                    "{}"
                ).format(
                    remote_filename, self._get_server_name(), error.message
                )
            else:
                remote_dir = remote_filename.split(".")[0]

                if isinstance(error, ClientResponseError):
                    message = _(
                        "It seems you don't have permissions to read the "
                        "directory <b>{}</b> in server <b>{}</b>."
                    ).format(remote_dir, self._get_server_name())
                else:
                    message = _(
                        "An error occurred while trying to download the "
                        "directory <b>{}</b> as a zip file from server "
                        "<b>{}</b>:"
                        "<br><br>"
                        "{}"
                    ).format(
                        remote_dir, self._get_server_name(), error.message
                    )

        if download_error:
            QMessageBox.critical(self, _("Download error"), message)
        elif os.path.isdir(local_directory):
            # Local filename
            local_filename = os.path.join(local_directory, remote_filename)

            # Write remote contents to local file
            try:
                with open(local_filename, "w") as download_file:
                    download_file.write(data)
            except TypeError:
                with open(local_filename, "wb") as download_file:
                    download_file.write(data)

        if self._files_to_download[self.server_id] > 0:
            self._files_to_download[self.server_id] -= 1

        if not self._operation_in_progress:
            self.sig_stop_spinner_requested.emit()

    @AsyncDispatcher(loop="explorer")
    async def _do_remote_download_directory(self, path):
        if not self.remote_files_manager:
            self.sig_stop_spinner_requested.emit()
            return

        zip_generator = self.remote_files_manager.zip_directory(path)
        zip_data = io.BytesIO()
        async for data in zip_generator:
            zip_data.write(data)
        zip_data.seek(0)
        return zip_data.getbuffer()

    @AsyncDispatcher(loop="explorer")
    async def _do_remote_download_file(self, path):
        if not self.remote_files_manager:
            self.sig_stop_spinner_requested.emit()
            return

        try:
            async with await self.remote_files_manager.open(
                path, mode="r"
            ) as file_manager:
                return await file_manager.read()
        except RemoteFileServicesError:
            async with await self.remote_files_manager.open(
                path, mode="rb"
            ) as file_manager:
                return await file_manager.read()

    @AsyncDispatcher.QtSlot
    def _on_remote_upload_file(self, future):
        self._handle_future_response_error(
            future,
            _("Upload error"),
            _("An error occured while trying to upload a file"),
        )

        if self._files_to_upload[self.server_id] > 0:
            self._files_to_upload[self.server_id] -= 1

        self.refresh(force_current=True)

    @AsyncDispatcher(loop="explorer")
    async def _do_remote_upload_file(self, local_path):
        if not self.remote_files_manager:
            self.sig_stop_spinner_requested.emit()
            return

        file_content = None
        remote_file = posixpath.join(
            self.root_prefix[self.server_id], os.path.basename(local_path)
        )

        try:
            with open(local_path, mode="r") as local_file:
                file_content = local_file.read()
            mode = "w"
        except UnicodeDecodeError:
            with open(local_path, mode="rb") as local_file:
                file_content = local_file.read()
            mode="wb"

        if file_content:
            async with await self.remote_files_manager.open(
                remote_file, mode=mode
            ) as file_manager:
                return await file_manager.write(file_content)

    @AsyncDispatcher.QtSlot
    def _on_remote_ls(self, future):
        error = self._handle_future_response_error(
            future,
            _("List contents error"),
            _("An error occured while trying to view a directory"),
        )

        if not error:
            data = future.result()
            self.set_files(data)
        else:
            # Set parent directory as root because the selected one can't be
            # accessed
            self.chdir(os.path.dirname(self.root_prefix[self.server_id]))

        if not self._operation_in_progress:
            self.sig_stop_spinner_requested.emit()

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
                file_name = os.path.relpath(
                    file["name"], self.root_prefix[self.server_id]
                )
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
        except SpyderRemoteSessionClosed:
            self.remote_files_manager = None

        return files

    def _on_check_if_remote_files_exist(
        self, future, operation: RemoteExistenceOperations
    ):
        self._handle_future_response_error(
            future,
            _("Upload error"),
            _("An error occured while trying to upload files"),
        )

        yes_to_all = False
        paths_existence = future.result()

        if len(paths_existence) > 1:
            buttons = (
                QMessageBox.Yes
                | QMessageBox.YesToAll
                | QMessageBox.No
                | QMessageBox.Cancel
            )
        else:
            buttons = QMessageBox.Yes | QMessageBox.No

        for path, response in paths_existence:
            filename = os.path.basename(path)
            files_counter = None

            if not yes_to_all and response["exists"]:
                if operation == RemoteExistenceOperations.Paste:
                    opening_sentence = _(
                        "The file <b>{}</b> that you're trying to paste on "
                        "the server <b>{}</b> already exists in the current "
                        "location."
                    )

                    files_counter = self._files_to_paste
                elif operation == RemoteExistenceOperations.Upload:
                    opening_sentence = _(
                        "The file <b>{}</b> that you're trying to upload to "
                        "the server <b>{}</b> already exists in the current "
                        "location."
                    )

                    files_counter = self._files_to_upload
                elif operation in [
                    RemoteExistenceOperations.NewFile,
                    RemoteExistenceOperations.NewFileWithContent,
                ]:
                    opening_sentence = _(
                        "The file <b>{}</b> that you're trying to create on "
                        "the server <b>{}</b> already exists in the current "
                        "location."
                    )
                elif (
                    operation
                    == RemoteExistenceOperations.NewDirectoryWithContent
                ):
                    # Show the same message as the one for empty directories.
                    opening_sentence = _(
                        "An error occurred while trying to create a file/"
                        "directory"
                    )
                    msg = (
                        opening_sentence
                        + "<br><br>"
                        + "[Errno 17] File exists: '{}'".format(path)
                    )

                    QMessageBox.critical(self, _("Error"), msg)
                    self.sig_stop_spinner_requested.emit()
                    return

                msg = (
                    opening_sentence.format(filename, self._get_server_name())
                    + "<br><br>"
                    + _("Do you want to overwrite it?")
                )
                answer = QMessageBox.warning(
                    self,
                    _("Overwrite file"),
                    msg,
                    buttons,
                )

                if answer == QMessageBox.YesToAll:
                    yes_to_all = True
                elif answer == QMessageBox.No:
                    if (
                        files_counter is not None
                        and files_counter[self.server_id] > 0
                    ):
                        files_counter[self.server_id] -= 1

                    if not self._operation_in_progress:
                        self.sig_stop_spinner_requested.emit()

                    continue
                elif answer == QMessageBox.Cancel:
                    if files_counter is not None:
                        files_counter[self.server_id] = 0

                    if not self._operation_in_progress:
                        self.sig_stop_spinner_requested.emit()

                    return

            if operation == RemoteExistenceOperations.Paste:
                new_path = posixpath.join(
                    self.root_prefix[self.server_id], filename
                )
                self._do_remote_paste(path, new_path).connect(
                    self._on_remote_paste
                )
            elif operation == RemoteExistenceOperations.Upload:
                self._do_remote_upload_file(path).connect(
                    self._on_remote_upload_file
                )
            elif operation == RemoteExistenceOperations.NewFile:
                self._do_remote_new(path, for_file=True).connect(
                    self._on_remote_new
                )
            elif operation == RemoteExistenceOperations.NewFileWithContent:
                file_content, __, __ = get_default_file_content(
                    get_conf_path("template.py")
                )
                self._do_remote_new_module(path, file_content).connect(
                    self._on_remote_new_module
                )
            elif (
                operation == RemoteExistenceOperations.NewDirectoryWithContent
            ):
                @AsyncDispatcher.QtSlot
                def remote_package(future):
                    self._on_remote_new_package(future, filename)

                self._do_remote_new(path).connect(remote_package)

    @AsyncDispatcher(loop="explorer")
    async def _check_if_remote_files_exist(self, paths: list[str]):
        """Check if remote files exist in the remote cwd."""
        paths_existence = []

        for path in paths:
            remote_file = posixpath.join(
                self.root_prefix[self.server_id], os.path.basename(path)
            )

            paths_existence.append(
                (path, await self.remote_files_manager.exists(remote_file))
            )

        return paths_existence

    async def _get_extra_files(self, generator, already_added):
        self.extra_files = []
        self.more_files_available = False
        async for file in generator:
            if len(self.extra_files) + already_added == self.get_conf(
                "max_files_display"
            ):
                self.more_files_available = True
                break

            file_name = os.path.relpath(
                file["name"], self.root_prefix[self.server_id]
            )
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
        new_path = posixpath.join(self.root_prefix[self.server_id], new_name)

        if for_file:
            # Check if remote file with the same name exists before trying to
            # create it.
            self._check_if_remote_files_exist([new_path]).connect(
                AsyncDispatcher.QtSlot(
                    functools.partial(
                        self._on_check_if_remote_files_exist,
                        operation=(
                            RemoteExistenceOperations.NewFileWithContent
                            if with_content
                            else RemoteExistenceOperations.NewFile
                        ),
                    )
                )
            )
        else:
            if with_content:
                # This is necessary because although an existing directory is
                # not overwritten by the files API, an __init__.py file inside
                # it is.
                self._check_if_remote_files_exist([new_path]).connect(
                    AsyncDispatcher.QtSlot(
                        functools.partial(
                            self._on_check_if_remote_files_exist,
                            operation=(
                                RemoteExistenceOperations.NewDirectoryWithContent
                            ),
                        )
                    )
                )
            else:
                # No need to check for existence because the files API raises
                # an error.
                self._do_remote_new(new_path, for_file=False).connect(
                    self._on_remote_new
                )

        self.sig_start_spinner_requested.emit()

    def _get_selected_indexes(self):
        indexes = self.view.selectedIndexes()
        if not indexes:
            return []

        # Indexes corresponding to columns other than the first are not
        # necessary because the info we need for multi-file operations is
        # available in the first one.
        return [idx for idx in indexes if idx.column() == 0]

    def _get_server_name(self):
        if (
            self.get_conf(
                f"{self.server_id}/client_type", section="remoteclient"
            )
            == ClientType.SSH
        ):
            auth_method = self.get_conf(
                f"{self.server_id}/auth_method", section="remoteclient"
            )
            name = self.get_conf(
                f"{self.server_id}/{auth_method}/name", section="remoteclient"
            )
        else:
            name = self.get_conf(
                f"{self.server_id}/jupyterhub_login/name",
                section="remoteclient",
            )

        return name

    def _register_shortcut_for_action(self, shortcut, action):
        action.setShortcut(QKeySequence(shortcut))

    def _register_shortcuts(self):
        """
        Register shortcuts for several actions.

        We have to do this to use the same shortcuts as the ones set for the
        local explorer without adding to Preferences more entries with
        different ids for the same actions.
        """
        for name, action in [
            ("copy file", self.copy_action),
            ("paste file", self.paste_action),
            ("copy absolute path", self.copy_path_action),
        ]:
            # This is necessary so that the shortcut options emit a
            # notification when changed in Preferneces.
            data = ShortcutData(
                qobject=None,
                name=name,
                context=self.CONF_SECTION,
            )
            SHORTCUTS_FOR_WIDGETS_DATA.append(data)

            # Add observer for shortcut to update it in its corresponding
            # action
            self.add_configuration_observer(
                functools.partial(
                    self._register_shortcut_for_action,
                    action=action,
                ),
                option=f"{self.CONF_SECTION}/{name}",
                section="shortcuts",
            )

    def _format_file_size(self, size):
        """
        Format file size using the same format used by Qt for local files.

        Adapted from https://stackoverflow.com/a/58201995/438386
        """
        units = ['bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', "EiB", "ZiB"]
        index = 0

        if size > 0:
            while size >= 1024:
                size /= 1024
                index += 1

            formatted_size = f"{size:.2f}"
        else:
            formatted_size = "0"

        return f'{formatted_size} {units[index]}'

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts and special keys."""
        key_seq = keyevent_to_keysequence_str(event)

        if event.key() == Qt.Key_F2:
            self.rename_items()
        elif event.key() == Qt.Key_Delete:
            self.delete_items()
        elif event.key() == Qt.Key_Backspace:
            self.go_to_parent_directory()
        elif key_seq == self.copy_action.shortcut().toString():
            self.copy_items()
        elif key_seq == self.paste_action.shortcut().toString():
            self.paste_items()
        elif key_seq == self.copy_path_action.shortcut().toString():
            self.copy_paths()
        else:
            super().keyPressEvent(event)

    # ---- Public API
    # -------------------------------------------------------------------------
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

        if directory == self.root_prefix.get(server_id):
            return

        if server_id:
            self.server_id = server_id
        self.root_prefix[self.server_id] = directory
        if remote_files_manager:
            self.remote_files_manager = remote_files_manager
        self.refresh(force_current=True)
        if emit:
            self.sig_dir_opened.emit(directory, self.server_id)

    def set_files(self, files, reset=True):
        if reset:
            # This is necessary to prevent an error when closing Spyder with
            # mixed local and remote consoles.
            try:
                self.model.setRowCount(0)
            except RuntimeError:
                pass

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
                name = os.path.relpath(path, self.root_prefix[self.server_id])

                file_type = file["type"]
                icon = ima.icon("FileIcon")
                if file_type == "directory":
                    icon = ima.icon("DirClosedIcon")

                file_name = QStandardItem(icon, name)
                file_name.setData(file)
                file_name.setToolTip(file["name"])

                if file_type == "directory":
                    file_size = QStandardItem("")
                else:
                    file_size = QStandardItem(
                        self._format_file_size(file["size"])
                    )
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
        self.root_prefix[self.server_id] = folder
        return self.model.invisibleRootItem()

    def get_current_folder(self):
        return self.root_prefix[self.server_id]

    def go_to_parent_directory(self):
        parent_directory = os.path.dirname(self.root_prefix[self.server_id])
        logger.debug(
            f"Going to parent directory of {self.root_prefix[self.server_id]}: "
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
                new_path = self.root_prefix.get(self.server_id)
            self._do_remote_ls(new_path, self.server_id).connect(
                self._on_remote_ls
            )

        self.previous_action.setEnabled(False)
        self.next_action.setEnabled(False)

        if self.histindex is not None:
            self.previous_action.setEnabled(self.histindex > 0)
            self.next_action.setEnabled(self.histindex < len(self.history) - 1)

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

    def copy_items(self):
        indexes = self._get_selected_indexes()
        if not indexes:
            return

        self._files_to_copy[self.server_id] = []
        for index in indexes:
            source_index = self.proxy_model.mapToSource(index)
            data_index = self.model.index(source_index.row(), 0)
            data = self.model.data(data_index, Qt.UserRole + 1)
            if data:
                self._files_to_copy[self.server_id].append(data["name"])

    def paste_items(self):
        if not self._files_to_copy.get(self.server_id, []):
            return

        if self.server_id not in self._files_to_paste:
            self._files_to_paste[self.server_id] = 0
        self._files_to_paste[self.server_id] += len(self._files_to_copy)
        self.sig_start_spinner_requested.emit()

        check_for_files_existence = True
        if self._files_to_paste[self.server_id] > 50:
            answer = QMessageBox.warning(
                self,
                _("Existence check"),
                _(
                    "You are about to paste more than 50 files in server "
                    "<b>{}</b>."
                    "<br><br>"
                    "Do you prefer to skip checking whether they exist in the "
                    "server to paste them more quickly?"
                ).format(self._get_server_name()),
                QMessageBox.Yes | QMessageBox.No,
            )

            if answer == QMessageBox.Yes:
                check_for_files_existence = False

        if check_for_files_existence:
            # Check if the remote files exist first. If some of them do, then
            # ask the user if they want to overwrite them with the files to be
            # pasted.
            self._check_if_remote_files_exist(
                self._files_to_copy[self.server_id]
            ).connect(
                AsyncDispatcher.QtSlot(
                    functools.partial(
                        self._on_check_if_remote_files_exist,
                        operation=RemoteExistenceOperations.Paste,
                    )
                )
            )
        else:
            for file in self._files_to_copy[self.server_id]:
                new_path = posixpath.join(
                    self.root_prefix[self.server_id], os.path.basename(file)
                )
                self._do_remote_paste(file, new_path).connect(
                    self._on_remote_paste
                )

    def rename_items(self):
        indexes = self._get_selected_indexes()
        if not indexes:
            return

        if self.server_id not in self._files_to_rename:
            self._files_to_rename[self.server_id] = 0
        self._files_to_rename[self.server_id] += len(indexes)
        self.sig_start_spinner_requested.emit()

        for index in indexes:
            source_index = self.proxy_model.mapToSource(index)
            data_index = self.model.index(source_index.row(), 0)
            data = self.model.data(data_index, Qt.UserRole + 1)
            if data:
                old_path = data["name"]
                relpath = os.path.relpath(
                    old_path, self.root_prefix[self.server_id]
                )
                new_relpath, valid = QInputDialog.getText(
                    self,
                    _("Rename"),
                    _("New name for <b>{}</b>:").format(relpath),
                    QLineEdit.Normal,
                    relpath,
                )
                if valid:
                    new_path = posixpath.join(
                        self.root_prefix[self.server_id], new_relpath
                    )
                    self._do_remote_rename(old_path, str(new_path)).connect(
                        self._on_remote_rename
                    )

    def copy_paths(self):
        paths = []
        indexes = self._get_selected_indexes()
        if not indexes or not self.view.currentIndex().isValid():
            paths.append(self.root_prefix[self.server_id])
        else:
            for index in indexes:
                source_index = self.proxy_model.mapToSource(index)
                data_index = self.model.index(source_index.row(), 0)
                data = self.model.data(data_index, Qt.UserRole + 1)
                if data:
                    paths.append(data["name"])

        if len(paths) > 1:
            # TODO: Decide what format we want for multiple paths (i.e. local
            # explorer or this one).
            clipboard_paths = ' '.join(['"' + path + '"' for path in paths])
        else:
            clipboard_paths = '"' + paths[0] + '"'

        cb = QApplication.clipboard()
        cb.setText(clipboard_paths, mode=QClipboard.Mode.Clipboard)

    def delete_items(self):
        yes_to_all = False
        indexes = self._get_selected_indexes()
        if not indexes:
            return

        if len(indexes) > 1:
            buttons = (
                QMessageBox.Yes
                | QMessageBox.YesToAll
                | QMessageBox.No
                | QMessageBox.Cancel
            )
        else:
            buttons = QMessageBox.Yes | QMessageBox.No

        if self.server_id not in self._files_to_delete:
            self._files_to_delete[self.server_id] = 0
        self._files_to_delete[self.server_id] += len(indexes)
        self.sig_start_spinner_requested.emit()

        for index in indexes:
            source_index = self.proxy_model.mapToSource(index)
            data_index = self.model.index(source_index.row(), 0)
            data = self.model.data(data_index, Qt.UserRole + 1)
            if data:
                path = data["name"]
                filename = os.path.relpath(
                    path, self.root_prefix[self.server_id]
                )

                if not yes_to_all:
                    result = QMessageBox.warning(
                        self,
                        _("Delete"),
                        _(
                            "Do you really want to delete <b>{filename}</b>?"
                            "<br><br>"
                            "<b>Note</b>: The file/directory will be removed "
                            "permanently from the remote filesystem."
                        ).format(filename=filename),
                        buttons
                    )

                if result == QMessageBox.YesToAll:
                    yes_to_all = True
                elif result == QMessageBox.No:
                    if self._files_to_delete[self.server_id] > 0:
                        self._files_to_delete[self.server_id] -= 1

                    if not self._operation_in_progress:
                        self.sig_stop_spinner_requested.emit()

                    continue
                elif result == QMessageBox.Cancel:
                    self._files_to_delete[self.server_id] = 0

                    if not self._operation_in_progress:
                        self.sig_stop_spinner_requested.emit()

                    return

                if result == QMessageBox.Yes or yes_to_all:
                    is_file = data["type"] == "file"
                    self._do_remote_delete(path, is_file=is_file).connect(
                        self._on_remote_delete
                    )

    def download_items(self):
        indexes = self._get_selected_indexes()
        if not indexes:
            return

        # Directory where the files will be downloaded
        directory = getexistingdirectory(
            self, _("Download directory"), getcwd_or_home()
        )

        # This is necessary in case the user clicks Cancel in the dialog
        if not directory:
            return

        # Keep track of how many files will be downloaded to stop the spinner
        # when all of them are processed.
        if self.server_id not in self._files_to_download:
            self._files_to_download[self.server_id] = 0
        self._files_to_download[self.server_id] += len(indexes)
        self.sig_start_spinner_requested.emit()

        # Check if users want to overwrite all downloaded files
        yes_to_all = False

        # Buttons to show in the dialog that asks to overwrite files
        if len(indexes) > 1:
            buttons = (
                QMessageBox.Yes
                | QMessageBox.YesToAll
                | QMessageBox.No
                | QMessageBox.Cancel
            )
        else:
            buttons = QMessageBox.Yes | QMessageBox.No

        for index in indexes:
            source_index = self.proxy_model.mapToSource(index)
            data_index = self.model.index(source_index.row(), 0)
            data = self.model.data(data_index, Qt.UserRole + 1)
            if data:
                path = data["name"]
                filename = os.path.relpath(
                    path, self.root_prefix[self.server_id]
                )
                is_file = data["type"] == "file"
                remote_filename = filename if is_file else f"{filename}.zip"

                # Local filename
                local_filename = os.path.join(directory, remote_filename)

                # Check if a local file with the same name exists
                if not yes_to_all and os.path.exists(local_filename):
                    answer = QMessageBox.warning(
                        self,
                        _("Overwrite file"),
                        _(
                            "The file <b>{}</b> that you're trying to "
                            "download from server <b>{}</b> already exists in "
                            "the location you selected."
                            "<br><br>"
                            "Do you want to overwrite it?"
                        ).format(remote_filename, self._get_server_name()),
                        buttons,
                    )

                    if answer == QMessageBox.YesToAll:
                        yes_to_all = True
                    elif answer == QMessageBox.No:
                        if self._files_to_download[self.server_id] > 0:
                            self._files_to_download[self.server_id] -= 1

                        if not self._operation_in_progress:
                            self.sig_stop_spinner_requested.emit()

                        continue
                    elif answer == QMessageBox.Cancel:
                        self._files_to_download[self.server_id] = 0

                        if not self._operation_in_progress:
                            self.sig_stop_spinner_requested.emit()

                        return

                # Download file or directory
                method = (
                    self._do_remote_download_file
                    if is_file
                    else self._do_remote_download_directory
                )
                method(path).connect(
                    AsyncDispatcher.QtSlot(
                        functools.partial(
                            self._on_remote_download_file,
                            remote_filename=remote_filename,
                            local_directory=directory,
                            is_file=is_file,
                        )
                    )
                )

    def upload_files(self):
        local_paths, __ = getopenfilenames(
            self,
            _("Upload files"),
            getcwd_or_home(),
            _("All files") + " (*)",
        )

        local_paths = [path for path in local_paths if os.path.exists(path)]
        if not local_paths:
            return

        if self.server_id not in self._files_to_upload:
            self._files_to_upload[self.server_id] = 0
        self._files_to_upload[self.server_id] += len(local_paths)
        self.sig_start_spinner_requested.emit()

        check_for_files_existence = True
        if len(local_paths) > 50:
            answer = QMessageBox.warning(
                self,
                _("Existence check"),
                _(
                    "You are about to upload more than 50 files to server "
                    "<b>{}</b>."
                    "<br><br>"
                    "Do you prefer to skip checking whether they exist on the "
                    "server to upload them more quickly?"
                ).format(self._get_server_name()),
                QMessageBox.Yes | QMessageBox.No,
            )

            if answer == QMessageBox.Yes:
                check_for_files_existence = False

        if check_for_files_existence:
            # Check if the remote files exist first. If some of them do, then
            # ask the user if they want to overwrite them with the local files
            # to be uploaded.
            self._check_if_remote_files_exist(local_paths).connect(
                AsyncDispatcher.QtSlot(
                    functools.partial(
                        self._on_check_if_remote_files_exist,
                        operation=RemoteExistenceOperations.Upload,
                    )
                )
            )
        else:
            for path in local_paths:
                self._do_remote_upload_file(path).connect(
                    self._on_remote_upload_file
                )

    def reset(self, server_id):
        self.root_prefix[server_id] = None

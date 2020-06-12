# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Watcher to detect filesystem changes in the project's directory."""

# Standard lib imports
import logging

# Third-party imports
import watchdog
from qtpy.QtCore import QObject, Signal
from qtpy.QtWidgets import QMessageBox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Local imports
from spyder.api.translations import get_translation

_ = get_translation("spyder")
logger = logging.getLogger(__name__)


class BaseThreadWrapper(watchdog.utils.BaseThread):
    """
    Wrapper around watchdog BaseThread class.
    This is necessary for issue spyder-ide/spyder#11370
    """
    queue = None

    def __init__(self):
        super().__init__()
        self._original_run = self.run
        self.run = self.run_wrapper

    def run_wrapper(self):
        try:
            self._original_run()
        except OSError as e:
            logger.exception('Watchdog thread exited with error %s',
                             e.strerror)
            self.queue.put(e)


# Monkeypatching BaseThread to prevent the error reported in
# spyder-ide/spyder#11370
watchdog.utils.BaseThread = BaseThreadWrapper


class WorkspaceEventHandler(QObject, FileSystemEventHandler):
    """
    Event handler for watchdog notifications.

    This class receives notifications about file/folder moving, modification,
    creation and deletion and emits a corresponding signal about it.
    """

    sig_file_moved = Signal(str, str)
    """
    This signal is emitted to inform a file has been moved.

    Parameters
    ----------
    old_path: str
        Old path for moved file.
    new_path: str
        New path for moved file.
    """

    sig_file_created = Signal(str)
    """
    This signal is emitted to inform a file has been created.

    Parameters
    ----------
    path: str
        New file path.
    """

    sig_file_deleted = Signal(str)
    """
    This signal is emitted to inform a file has been deleted.

    Parameters
    ----------
    path: str
        Deleted file path.
    """

    sig_file_modified = Signal(str)
    """
    This signal is emitted to inform a file has been modified.

    Parameters
    ----------
    path: str
        Modified file path.
    """

    sig_folder_moved = Signal(str, str)
    """
    This signal is emitted to inform a folder has been moved.

    Parameters
    ----------
    old_path: str
        Old path for moved folder.
    new_path: str
        New path for moved folder.
    """

    sig_folder_created = Signal(str)
    """
    This signal is emitted to inform a folder has been created.

    Parameters
    ----------
    path: str
        New folder path.
    """

    sig_folder_deleted = Signal(str)
    """
    This signal is emitted to inform a folder has been deleted.

    Parameters
    ----------
    path: str
        Deleted folder path.
    """

    sig_folder_modified = Signal(str)
    """
    This signal is emitted to inform a folder has been modified.

    Parameters
    ----------
    path: str
        Modified folder path.
    """

    def __init__(self, parent=None):
        super().__init__()
        self.setParent(parent)

    @staticmethod
    def _fmt(is_dir):
        return 'directory' if is_dir else 'file'

    def on_moved(self, event):
        src_path = event.src_path
        dest_path = event.dest_path
        is_dir = event.is_directory
        logger.info("Moved {0}: {1} to {2}".format(
            self._fmt(is_dir), src_path, dest_path))

        if is_dir:
            self.sig_folder_moved.emit(src_path, dest_path)
        else:
            self.sig_file_moved.emit(src_path, dest_path)

    def on_created(self, event):
        src_path = event.src_path
        is_dir = event.is_directory
        logger.info("Created {0}: {1}".format(
            self._fmt(is_dir), src_path))

        if is_dir:
            self.sig_folder_created.emit(src_path)
        else:
            self.sig_file_created.emit(src_path)

    def on_deleted(self, event):
        src_path = event.src_path
        is_dir = event.is_directory
        logger.info("Deleted {0}: {1}".format(
            self._fmt_is_dir(is_dir), src_path))

        if is_dir:
            self.sig_folder_deleted.emit(src_path)
        else:
            self.sig_file_deleted.emit(src_path)

    def on_modified(self, event):
        src_path = event.src_path
        is_dir = event.is_directory
        logger.info("Modified {0}: {1}".format(
            self._fmt(is_dir), src_path))

        if is_dir:
            self.sig_folder_modified.emit(src_path)
        else:
            self.sig_file_modified.emit(src_path)


class WorkspaceWatcher(QObject):
    """
    Wrapper class around watchdog observer and notifier.

    It provides methods to start and stop watching folders.
    """

    sig_file_moved = Signal(str, str)
    """
    This signal is emitted to inform a file has been moved.

    Parameters
    ----------
    old_path: str
        Old path for moved file.
    new_path: str
        New path for moved file.
    """

    sig_file_created = Signal(str)
    """
    This signal is emitted to inform a file has been created.

    Parameters
    ----------
    path: str
        New file path.
    """

    sig_file_deleted = Signal(str)
    """
    This signal is emitted to inform a file has been deleted.

    Parameters
    ----------
    path: str
        Deleted file path.
    """

    sig_file_modified = Signal(str)
    """
    This signal is emitted to inform a file has been modified.

    Parameters
    ----------
    path: str
        Modified file path.
    """

    sig_folder_moved = Signal(str, str)
    """
    This signal is emitted to inform a folder has been moved.

    Parameters
    ----------
    old_path: str
        Old path for moved folder.
    new_path: str
        New path for moved folder.
    """

    sig_folder_created = Signal(str)
    """
    This signal is emitted to inform a folder has been created.

    Parameters
    ----------
    path: str
        New folder path.
    """

    sig_folder_deleted = Signal(str)
    """
    This signal is emitted to inform a folder has been deleted.

    Parameters
    ----------
    path: str
        Deleted folder path.
    """

    sig_folder_modified = Signal(str)
    """
    This signal is emitted to inform a folder has been modified.

    Parameters
    ----------
    path: str
        Modified folder path.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.observer = None
        self.event_handler = WorkspaceEventHandler(self)

        # Signals
        self.event_handler.sig_file_created.connect(self.sig_file_created)
        self.event_handler.sig_file_moved.connect(self.sig_file_moved)
        self.event_handler.sig_file_deleted.connect(self.sig_file_deleted)
        self.event_handler.sig_file_modified.connect(self.sig_file_modified)
        self.event_handler.sig_folder_created.connect(self.sig_folder_created)
        self.event_handler.sig_folder_moved.connect(self.sig_folder_moved)
        self.event_handler.sig_folder_deleted.connect(self.sig_folder_deleted)
        self.event_handler.sig_folder_modified.connect(self.sig_folder_modified)

    def start(self, workspace_folder):
        # Needed to handle an error caused by the inotify limit reached.
        # See spyder-ide/spyder#10478
        try:
            self.observer = Observer()
            self.observer.schedule(
                self.event_handler, workspace_folder, recursive=True)
            self.observer.start()
        except OSError as error:
            if u'inotify' in str(error):
                QMessageBox.warning(
                    self.parent(),
                    "Spyder",
                    _("File system changes for this project can't be tracked "
                      "because it contains too many files. To fix this you "
                      "need to increase the inotify limit in your system, "
                      "with the following command:"
                      "<br><br>"
                      "<code>"
                      "sudo sysctl -n -w fs.inotify.max_user_watches=524288"
                      "</code>"
                      "<br><br>For a permanent solution you need to add to"
                      "<code>/etc/sysctl.conf</code>"
                      "the following line:<br><br>"
                      "<code>"
                      "fs.inotify.max_user_watches=524288"
                      "</code>"
                      "<br><br>"
                      "After doing that, you need to close and start Spyder "
                      "again so those changes can take effect."))
                self.observer = None
            else:
                raise error

    def stop(self):
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            del self.observer

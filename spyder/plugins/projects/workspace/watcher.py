# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard lib imports
import logging

# Third-party imports
from qtpy.QtCore import QObject, Signal

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)


class WorkspaceEventHandler(QObject, FileSystemEventHandler):
    """Event handler for watchdog notifications. This class recieves
       notifications about file/folder moving, modification,
       creation and deletion and emits its corresponding signal."""

    sig_file_moved = Signal(str, str, bool)
    sig_file_created = Signal(str, bool)
    sig_file_deleted = Signal(str, bool)
    sig_file_modified = Signal(str, bool)

    def fmt_is_dir(self, is_dir):
        return 'directory' if is_dir else 'file'

    def on_moved(self, event):
        src_path = event.src_path
        dest_path = event.dest_path
        is_dir = event.is_directory
        logger.info("Moved {0}: {1} to {2}".format(
            self.fmt_is_dir(is_dir), src_path, dest_path))
        self.sig_file_moved.emit(src_path, dest_path, is_dir)

    def on_created(self, event):
        src_path = event.src_path
        is_dir = event.is_directory
        logger.info("Created {0}: {1}".format(
            self.fmt_is_dir(is_dir), src_path))
        self.sig_file_created.emit(src_path, is_dir)

    def on_deleted(self, event):
        src_path = event.src_path
        is_dir = event.is_directory
        logger.info("Deleted {0}: {1}".format(
            self.fmt_is_dir(is_dir), src_path))
        self.sig_file_deleted.emit(src_path, is_dir)

    def on_modified(self, event):
        src_path = event.src_path
        is_dir = event.is_directory
        logger.info("Modified {0}: {1}".format(
            self.fmt_is_dir(is_dir), src_path))
        self.sig_file_modified.emit(src_path, is_dir)


class WorkspaceWatcher(QObject):
    """Wrapper class around watchdog observer and notifier. Provides methods
       to start and stop watching folders."""

    def __init__(self):
        self.observer = None
        self.event_handler = WorkspaceEventHandler()

    def connect_signals(self, project_manager):
        pass

    def disconnect_signals(self):
        self.event_handler.sig_file_created.disconnect()
        self.event_handler.sig_file_deleted.disconnect()
        self.event_handler.sig_file_moved.disconnect()
        self.event_handler.sig_file_modified.disconnect()

    def start(self, workspace_folder):
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler, workspace_folder, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
        del self.observer

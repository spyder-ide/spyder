# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Watcher to detect filesystem changes in the project's directory."""

# Standard lib imports
import os
import logging
from pathlib import Path

# Third-party imports
from qtpy.QtCore import QObject, Signal
from superqt.utils import qthrottled
import watchdog
from watchdog.events import FileSystemEventHandler, PatternMatchingEventHandler
from watchdog.observers.polling import PollingObserverVFS

# Local imports
from spyder.config.utils import EDIT_EXTENSIONS


# ---- Constants
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

FOLDERS_TO_IGNORE = [
    "__pycache__",
    "build",
]


# ---- Monkey patches
# -----------------------------------------------------------------------------
class BaseThreadWrapper(watchdog.utils.BaseThread):
    """
    Wrapper around watchdog BaseThread class.
    This is necessary for issue spyder-ide/spyder#11370
    """
    queue = None

    def __init__(self):
        super(BaseThreadWrapper, self).__init__()
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


# ---- Auxiliary functions
# -----------------------------------------------------------------------------
def ignore_entry(entry: os.DirEntry) -> bool:
    """Check if an entry should be ignored."""
    parts = Path(entry.path).parts

    # Ignore files in hidden directories (e.g. .git)
    if any([p.startswith(".") for p in parts]):
        return True

    # Ignore specific folders
    for folder in FOLDERS_TO_IGNORE:
        if folder in parts:
            return True

    return False


def editable_file(entry: os.DirEntry) -> bool:
    """Check if an entry file is editable."""
    if entry.is_file():
        return (os.path.splitext(entry.path)[1] in EDIT_EXTENSIONS)
    return True


def filter_scandir(path):
    """
    Filter entries from os.scandir that we're not interested in tracking in the
    observer.
    """
    return (
        entry for entry in os.scandir(path)
        if (not ignore_entry(entry) and editable_file(entry))
    )


# ---- Event handler
# -----------------------------------------------------------------------------
class WorkspaceEventHandler(QObject, PatternMatchingEventHandler):
    """
    Event handler for watchdog notifications.

    This class receives notifications about file/folder moving, modification,
    creation and deletion and emits a corresponding signal about it.
    """

    sig_file_moved = Signal(str, str, bool)
    sig_file_created = Signal(str, bool)
    sig_file_deleted = Signal(str, bool)
    sig_file_modified = Signal(str, bool)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        PatternMatchingEventHandler.__init__(
            self,
            patterns=[f"*{ext}" for ext in EDIT_EXTENSIONS],
        )

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

    def dispatch(self, event):
        # Don't apply patterns to directories, only to files
        if event.is_directory:
            FileSystemEventHandler.dispatch(self, event)
        else:
            super().dispatch(event)


# ---- Watcher
# -----------------------------------------------------------------------------
class WorkspaceWatcher(QObject):
    """
    Wrapper class around watchdog observer and notifier.

    It provides methods to start and stop watching folders.
    """

    observer = None

    sig_file_moved = Signal(str, str, bool)
    sig_file_created = Signal(str, bool)
    sig_file_deleted = Signal(str, bool)
    sig_file_modified = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.event_handler = WorkspaceEventHandler(self)

        self.event_handler.sig_file_moved.connect(self.on_moved)
        self.event_handler.sig_file_created.connect(self.on_created)
        self.event_handler.sig_file_deleted.connect(self.on_deleted)
        self.event_handler.sig_file_modified.connect(self.on_modified)

    def connect_signals(self, project):
        self.sig_file_created.connect(project.file_created)
        self.sig_file_moved.connect(project.file_moved)
        self.sig_file_deleted.connect(project.file_deleted)
        self.sig_file_modified.connect(project.file_modified)

    def start(self, workspace_folder):
        # We use a polling observer because:
        # * It doesn't introduce long freezes on Linux when switching git
        #   branches that have many changes between them. That's because the
        #   OS-based observer (i.e. inotify) generates way too many events.
        # * The OS-based observer on Windows has many shortcomings (see
        #   openmsi/openmsistream#56).
        # * There doesn't seem to be issues on Mac, but it's simpler to use a
        #   single observer for all OSes.
        self.observer = PollingObserverVFS(
            stat=os.stat, listdir=filter_scandir
        )

        self.observer.schedule(
            self.event_handler, workspace_folder, recursive=True
        )

        try:
            self.observer.start()
        except Exception:
            logger.debug(
                f"Observer could not be started for: {workspace_folder}."
            )

    def stop(self):
        if self.observer is not None:
            # This is required to avoid showing an error when closing
            # projects.
            # Fixes spyder-ide/spyder#14107
            try:
                self.observer.stop()
                self.observer.join()
                del self.observer
                self.observer = None
            except RuntimeError:
                pass

    @qthrottled(timeout=200)
    def on_moved(self, src_path, dest_path, is_dir):
        self.sig_file_moved.emit(src_path, dest_path, is_dir)

    @qthrottled(timeout=200)
    def on_created(self, path, is_dir):
        self.sig_file_created.emit(path, is_dir)

    @qthrottled(timeout=200)
    def on_deleted(self, path, is_dir):
        self.sig_file_deleted.emit(path, is_dir)

    @qthrottled(timeout=200)
    def on_modified(self, path, is_dir):
        self.sig_file_modified.emit(path, is_dir)

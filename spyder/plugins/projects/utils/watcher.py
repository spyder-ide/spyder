# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Watcher to detect filesystem changes in the project's directory."""

# Standard lib imports
import os
import logging
import stat

# Third-party imports
from qtpy.QtCore import QObject, Signal
from superqt.utils import qthrottled
import watchdog
from watchdog.events import FileSystemEventHandler, PatternMatchingEventHandler
from watchdog.observers.polling import PollingObserverVFS

# Local imports
from spyder.config.utils import EDIT_EXTENSIONS
from spyder.plugins.projects.utils.gitignore import (
    GitignoreRules, find_repository_root, read_gitignore)


# ---- Constants
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

FOLDERS_TO_IGNORE = {
    "__pycache__",
    "build",
}


# ---- Monkey patches
# -----------------------------------------------------------------------------
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


# ---- Auxiliary functions
# -----------------------------------------------------------------------------
def ignore_entry(
    entry: os.DirEntry, folders_to_ignore=FOLDERS_TO_IGNORE
) -> bool:
    """Check if an entry should be ignored."""
    # ignore any file/folder starting with a
    #  dot or in the folders_to_ignore set
    name = entry.name
    return name.startswith(".") or name in folders_to_ignore


def editable_file(entry: os.DirEntry) -> bool:
    """Check if an entry file is editable."""
    if entry.is_file():
        return (os.path.splitext(entry.name)[1] in EDIT_EXTENSIONS)
    return True


class ScandirFilter:
    """
    Replacement for os.scandir that drops the entries the observer shouldn't
    track.

    Parameters
    ----------
    root: str
        Folder being watched, exactly as passed to the observer.
    follow_gitignore: bool
        Also drop the paths matched by the .gitignore files in `root` and its
        subfolders, and, if `root` is inside a git repository, by those in
        the folders between it and the repository root and by the
        repository's info/exclude file. Unlike git, paths are dropped even if
        they're tracked, and `root` itself is never ignored.
    folders_to_ignore: iterable of str
        Entry names to drop in addition to `FOLDERS_TO_IGNORE`.
    """

    def __init__(self, root, follow_gitignore=True, folders_to_ignore=()):
        self.root = root
        self.follow_gitignore = follow_gitignore
        self.folders_to_ignore = FOLDERS_TO_IGNORE | set(folders_to_ignore)

        # Patterns are matched against paths relative to this folder
        # Resolved because find_repository_root resolves symlinks
        real_root = os.path.realpath(root)
        repo_root = find_repository_root(root) if follow_gitignore else None
        self._top = repo_root or real_root
        relative_root = os.path.relpath(real_root, self._top)
        self._root_prefix = (
            "" if relative_root == "." else
            "/".join(relative_root.split(os.sep)) + "/"
        )

        # Gitignore files above `root`, lowest precedence first
        self._outer_gitignores = []
        if repo_root is not None:
            self._outer_gitignores.append(
                (os.path.join(repo_root, ".git", "info", "exclude"), "")
            )
            folder, prefix = repo_root, ""
            for name in self._root_prefix.split("/")[:-1]:
                self._outer_gitignores.append(
                    (os.path.join(folder, ".gitignore"), prefix)
                )
                folder = os.path.join(folder, name)
                prefix += name + "/"

        # Keyed by chain: ((path, mtime_ns, size, prefix), ...)
        self._rules: dict[tuple[tuple[str, int, int, str], ...], GitignoreRules] = {(): GitignoreRules()}
        self._previous_rules: dict[tuple[tuple[str, int, int, str], ...], GitignoreRules] = {}

        # Chain and prefix of the folders to list in the current snapshot
        self._folders: dict[str, tuple[tuple[tuple[str, int, int, str], ...], str]] = {}

        # Keyed by path: (rules, is_dir, ignored)
        self._decisions: dict[str, tuple[GitignoreRules, bool, bool]] = {}
        self._previous_decisions: dict[str, tuple[GitignoreRules, bool, bool]] = {}
        self._warned_root_ignored = False

    def __call__(self, path: str) -> list[os.DirEntry]:
        entries = list(os.scandir(path))
        if self.follow_gitignore:
            chain, prefix = self._get_chain(path, entries)
            rules = self._get_rules(chain)

        kept = []
        for entry in entries:
            if (
                ignore_entry(entry, self.folders_to_ignore)
                or not editable_file(entry)
            ):
                continue

            if self.follow_gitignore:
                relative_path = prefix + entry.name  # type: ignore[assignment]
                # Git doesn't treat symlinks to folders as folders
                is_dir = entry.is_dir(follow_symlinks=False)
                decision = self._previous_decisions.get(entry.path)
                if (
                    decision is None
                    or decision[0] is not rules
                    or decision[1] != is_dir
                ):
                    decision = (
                        rules, is_dir, rules.ignores(relative_path, is_dir)
                    )
                self._decisions[entry.path] = decision
                if decision[2]:
                    continue
                # Files too, because one could be replaced by a folder before
                # the observer checks its type.
                self._folders[entry.path] = (chain, relative_path + "/")

            kept.append(entry)

        if (
            path == self.root
            and not kept
            and not self._warned_root_ignored
            and any(
                not ignore_entry(entry, self.folders_to_ignore)
                and editable_file(entry)
                for entry in entries
            )
        ):
            self._warned_root_ignored = True
            logger.warning(
                f"All files and folders in {self.root} are ignored by "
                f".gitignore files, so the watcher won't report changes in it"
            )

        return kept

    def _get_chain(self, path: str, entries: list[os.DirEntry]) -> tuple[tuple[tuple[str, int, int, str], ...], str]:
        """Get the gitignore files that apply to `path` and its prefix."""
        # The observer starts every snapshot by listing the root
        if path == self.root:
            self._previous_rules, self._rules = (
                self._rules, {(): GitignoreRules()}
            )
            self._previous_decisions, self._decisions = self._decisions, {}
            self._folders = {}

            chain: tuple[tuple[str, int, int, str], ...] = ()
            for gitignore, prefix in self._outer_gitignores:
                try:
                    st = os.stat(gitignore)
                except OSError:
                    continue
                # Reading a FIFO would block
                if stat.S_ISREG(st.st_mode):
                    chain += (
                        (gitignore, st.st_mtime_ns, st.st_size, prefix),
                    )
            prefix = self._root_prefix
        else:
            chain, prefix = self._folders[path]

        for entry in entries:
            if entry.name == ".gitignore" and entry.is_file():
                try:
                    st = entry.stat()
                except OSError:
                    break
                chain += ((entry.path, st.st_mtime_ns, st.st_size, prefix),)
                break

        return chain, prefix

    def _get_rules(self, chain: tuple[tuple[str, int, int, str], ...]) -> GitignoreRules:
        rules = self._rules.get(chain)
        if rules is None:
            rules = self._previous_rules.get(chain)
            if rules is None:
                gitignore, __, __, prefix = chain[-1]
                rules = self._get_rules(chain[:-1]).extended(
                    read_gitignore(gitignore, prefix)
                )
            self._rules[chain] = rules

        return rules


# ---- Event handler
# -----------------------------------------------------------------------------
class WorkspaceEventHandler(QObject, PatternMatchingEventHandler):
    # NOTE: QObject must stay first here, unlike our other multi-inheritance
    # classes. watchdog's PatternMatchingEventHandler.__init__ calls
    # super().__init__() internally; if QObject came after it in the MRO,
    # that call would re-enter QObject.__init__ a second time and Shiboken
    # aborts the process ("You can't initialize a QObject object twice").
    # With QObject first, the MRO puts PatternMatchingEventHandler's own
    # super() call past QObject already, so it safely reaches Handler's
    # non-Qt ancestor instead.
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
    scandir_filter = None
    _filter_settings = None

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

    def start(self, workspace_folder, follow_gitignore=True,
              folders_to_ignore=()):
        settings = (
            workspace_folder, follow_gitignore, frozenset(folders_to_ignore)
        )
        if settings != self._filter_settings:
            self.scandir_filter = ScandirFilter(
                workspace_folder, follow_gitignore, folders_to_ignore
            )
            self._filter_settings = settings

        # We use a polling observer because:
        # * It doesn't introduce long freezes on Linux when switching git
        #   branches that have many changes between them. That's because the
        #   OS-based observer (i.e. inotify) generates way too many events.
        # * The OS-based observer on Windows has many shortcomings (see
        #   openmsi/openmsistream#56).
        # * There doesn't seem to be issues on Mac, but it's simpler to use a
        #   single observer for all OSes.
        self.observer = PollingObserverVFS(
            stat=os.stat, listdir=self.scandir_filter
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

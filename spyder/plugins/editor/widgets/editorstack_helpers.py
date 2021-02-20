# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import logging

# Third party imports
from qtpy.QtCore import Signal, QFileInfo, QObject, QTimer, QThread
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.plugins.editor.utils.findtasks import find_tasks
from spyder.py3compat import to_text_string, MutableSequence

logger = logging.getLogger(__name__)


class AnalysisThread(QThread):
    """Analysis thread."""

    def __init__(self, parent, checker, source_code):
        """Initialize the Analysis thread."""
        super(AnalysisThread, self).__init__(parent)
        self.checker = checker
        self.results = None
        self.source_code = source_code

    def run(self):
        """Run analysis."""
        try:
            self.results = self.checker(self.source_code)
        except Exception as e:
            logger.error(e, exc_info=True)


class ThreadManager(QObject):
    """Analysis thread manager."""
    def __init__(self, parent, max_simultaneous_threads=2):
        """Initialize the ThreadManager."""
        super(ThreadManager, self).__init__(parent)
        self.max_simultaneous_threads = max_simultaneous_threads
        self.started_threads = {}
        self.pending_threads = []
        self.end_callbacks = {}

    def close_threads(self, parent):
        """Close threads associated to parent_id."""
        logger.debug("Call ThreadManager's 'close_threads'")
        if parent is None:
            # Closing all threads
            self.pending_threads = []
            threadlist = []
            for threads in list(self.started_threads.values()):
                threadlist += threads
        else:
            parent_id = id(parent)
            self.pending_threads = [(_th, _id) for (_th, _id)
                                    in self.pending_threads
                                    if _id != parent_id]
            threadlist = self.started_threads.get(parent_id, [])
        for thread in threadlist:
            logger.debug("Waiting for thread %r to finish" % thread)
            while thread.isRunning():
                # We can't terminate thread safely, so we simply wait...
                QApplication.processEvents()

    def close_all_threads(self):
        """Close all threads."""
        logger.debug("Call ThreadManager's 'close_all_threads'")
        self.close_threads(None)

    def add_thread(self, checker, end_callback, source_code, parent):
        """Add thread to queue."""
        parent_id = id(parent)
        thread = AnalysisThread(self, checker, source_code)
        self.end_callbacks[id(thread)] = end_callback
        self.pending_threads.append((thread, parent_id))
        logger.debug("Added thread %r to queue" % thread)
        QTimer.singleShot(50, self.update_queue)

    def update_queue(self):
        """Update queue."""
        started = 0
        for parent_id, threadlist in list(self.started_threads.items()):
            still_running = []
            for thread in threadlist:
                if thread.isFinished():
                    end_callback = self.end_callbacks.pop(id(thread))
                    if thread.results is not None:
                        #  The thread was executed successfully
                        end_callback(thread.results)
                    thread.setParent(None)
                    thread = None
                else:
                    still_running.append(thread)
                    started += 1
            threadlist = None
            if still_running:
                self.started_threads[parent_id] = still_running
            else:
                self.started_threads.pop(parent_id)
        logger.debug("Updating queue:")
        logger.debug("    started: %d" % started)
        logger.debug("    pending: %d" % len(self.pending_threads))
        if self.pending_threads and started < self.max_simultaneous_threads:
            thread, parent_id = self.pending_threads.pop(0)
            thread.finished.connect(self.update_queue)
            threadlist = self.started_threads.get(parent_id, [])
            self.started_threads[parent_id] = threadlist+[thread]
            logger.debug("===>starting: %r" % thread)
            thread.start()


class FileInfo(QObject):
    """File properties."""
    todo_results_changed = Signal()
    sig_save_bookmarks = Signal(str, str)
    text_changed_at = Signal(str, int)
    edit_goto = Signal(str, int, str)
    sig_send_to_help = Signal(str, str, bool)
    sig_filename_changed = Signal(str)
    sig_show_object_info = Signal(int)
    sig_show_completion_object_info = Signal(str, str)

    def __init__(self, filename, encoding, editor, new, threadmanager):
        """Initialize the FileInfo."""
        QObject.__init__(self)
        self.threadmanager = threadmanager
        self._filename = filename
        self.newly_created = new
        self.default = False      # Default untitled file
        self.encoding = encoding
        self.editor = editor
        self.path = []

        self.classes = (filename, None, None)
        self.todo_results = []
        self.lastmodified = QFileInfo(filename).lastModified()

        self.editor.textChanged.connect(self.text_changed)
        self.editor.sig_bookmarks_changed.connect(self.bookmarks_changed)
        self.editor.sig_show_object_info.connect(self.sig_show_object_info)
        self.editor.sig_show_completion_object_info.connect(
            self.sig_send_to_help)
        self.sig_filename_changed.connect(self.editor.sig_filename_changed)

    @property
    def filename(self):
        """Filename property."""
        return self._filename

    @filename.setter
    def filename(self, value):
        """Filename setter."""
        self._filename = value
        self.sig_filename_changed.emit(value)

    def text_changed(self):
        """Editor's text has changed."""
        self.default = False
        self.text_changed_at.emit(self.filename,
                                  self.editor.get_position('cursor'))

    def get_source_code(self):
        """Return associated editor source code."""
        return to_text_string(self.editor.toPlainText())

    def run_todo_finder(self):
        """Run TODO finder."""
        if self.editor.is_python_or_ipython():
            self.threadmanager.add_thread(find_tasks,
                                          self.todo_finished,
                                          self.get_source_code(), self)

    def todo_finished(self, results):
        """Code analysis thread has finished."""
        self.set_todo_results(results)
        self.todo_results_changed.emit()

    def set_todo_results(self, results):
        """Set TODO results and update markers in editor."""
        self.todo_results = results
        self.editor.process_todo(results)

    def cleanup_todo_results(self):
        """Clean-up TODO finder results."""
        self.todo_results = []

    def bookmarks_changed(self):
        """Bookmarks list has changed."""
        bookmarks = self.editor.get_bookmarks()
        if self.editor.bookmarks != bookmarks:
            self.editor.bookmarks = bookmarks
            self.sig_save_bookmarks.emit(self.filename, repr(bookmarks))


class StackHistory(MutableSequence):
    """Handles editor stack history.

    Works as a list of numbers corresponding to tab indexes.
    Internally elements are saved using objects id's.
    """

    def __init__(self, editor):
        """Initialize the StackHistory."""
        self.history = list()
        self.id_list = list()
        self.editor = editor

    def _update_id_list(self):
        """Update list of corresponding ids and tabs."""
        self.id_list = [id(self.editor.tabs.widget(_i))
                        for _i in range(self.editor.tabs.count())]

    def refresh(self):
        """Remove editors that are not longer open."""
        self._update_id_list()
        for _id in self.history[:]:
            if _id not in self.id_list:
                self.history.remove(_id)

    def __len__(self):
        """Return the length of the history."""
        return len(self.history)

    def __getitem__(self, i):
        """Retrieve the ith element of the history."""
        self._update_id_list()
        try:
            return self.id_list.index(self.history[i])
        except ValueError:
            self.refresh()
            raise IndexError

    def __delitem__(self, i):
        """Delete the ith element of the history."""
        del self.history[i]

    def __setitem__(self, i, v):
        """Set the ith element of the history."""
        _id = id(self.editor.tabs.widget(v))
        self.history[i] = _id

    def __str__(self):
        """Return the str."""
        return str(list(self))

    def insert(self, i, tab_index):
        """Insert the widget (at tab index) in the position i (index)."""
        _id = id(self.editor.tabs.widget(tab_index))
        self.history.insert(i, _id)

    def remove(self, tab_index):
        """Remove the widget at the corresponding tab_index."""
        _id = id(self.editor.tabs.widget(tab_index))
        if _id in self.history:
            self.history.remove(_id)

    def remove_and_append(self, index):
        """Remove previous entrances of a tab, and add it as the latest."""
        while index in self:
            self.remove(index)
        self.append(index)

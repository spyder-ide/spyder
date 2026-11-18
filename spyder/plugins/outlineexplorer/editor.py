# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Outline explorer editor proxy."""

# Standard library imports
import logging

from qtpy.QtCore import QTimer, Slot
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.plugins.outlineexplorer.api import OutlineExplorerProxy


# Logging
logger = logging.getLogger(__name__)


class OutlineExplorerProxyEditor(OutlineExplorerProxy):
    def __init__(self, editor, fname):
        super().__init__()
        self.setParent(editor)
        self._editor = editor
        self.fname = fname
        editor.sig_cursor_position_changed.connect(
            self.sig_cursor_position_changed)

        # This saves the symbols info that comes from the server.
        self.info = None

        # This is used to tell if the associated tree is updated with the
        # latest info available here
        self.is_tree_updated = False
        self._markdown_timer = None
        self._markdown_active = False
        self._markdown_worker = None

    def update_outline_info(self, info):
        logger.debug(
            f"Updating info for proxy {id(self)} of file {self.fname}"
        )
        self.sig_outline_explorer_data_changed.emit(info)
        self.info = info
        self.is_tree_updated = False

    def emit_request_in_progress(self):
        self.sig_start_outline_spinner.emit()

    def is_python(self):
        return self._editor.is_python()

    def is_python_or_ipython(self):
        return self._editor.is_python_or_ipython()

    def get_id(self):
        return self._editor.get_document_id()

    def get_language(self):
        return self._editor.language

    def give_focus(self):
        self._editor.clearFocus()
        self._editor.setFocus()

    def get_cursor_line_number(self):
        return self._editor.get_cursor_line_number()

    def get_line_count(self):
        return self._editor.get_line_count()

    def parent(self):
        return self._editor.parent()

    def outlineexplorer_data_list(self):
        """Get outline explorer data list."""
        return self._editor.outlineexplorer_data_list()

    def request_symbols(self):
        """Request current editor symbols."""
        if self.get_language().lower() == 'markdown':
            if self._markdown_timer is None:
                self._markdown_timer = QTimer(self)
                self._markdown_timer.setSingleShot(True)
                self._markdown_timer.setInterval(400)
                self._markdown_timer.timeout.connect(self._update_markdown)
                self._editor.textChanged.connect(self._schedule_markdown)
            self._schedule_markdown()
        else:
            if self._markdown_timer is not None:
                self._markdown_timer.stop()
            self._editor.request_symbols()

    def set_outline_active(self, active):
        self._markdown_active = active
        if active and self.get_language().lower() == 'markdown':
            self.request_symbols()
        elif self._markdown_timer is not None:
            self._markdown_timer.stop()

    def _schedule_markdown(self):
        if self._markdown_active:
            self._markdown_timer.start()

    def _update_markdown(self):
        if not self._markdown_active or self.get_language().lower() != 'markdown':
            return
        from spyder.plugins.outlineexplorer.markdown import markdown_symbols
        from spyder.utils.workers import WorkerManager
        document = self._editor.document()
        revision = document.revision()
        cache = getattr(document, '_markdown_outline', None)
        if cache is not None and cache[0] == revision:
            self.update_outline_info(cache[1])
            return
        worker = getattr(document, '_markdown_outline_pending', None)
        if worker is not None and worker.is_finished():
            document._markdown_outline_pending = worker = None
        if worker is None:
            app = QApplication.instance()
            if not hasattr(app, '_markdown_outline_workers'):
                app._markdown_outline_workers = WorkerManager(app, max_threads=1)
                app.aboutToQuit.connect(app._markdown_outline_workers.terminate_all)
            worker = app._markdown_outline_workers.create_python_worker(
                markdown_symbols, self._editor.toPlainText())
            worker.revision = revision
            document._markdown_outline_pending = worker
        if self._markdown_worker is not worker:
            self._markdown_worker = worker
            worker.sig_finished.connect(self._markdown_finished)
        worker.start()

    @Slot(object, object, object)
    def _markdown_finished(self, worker, symbols, error):
        if self._markdown_worker is not worker:
            return
        self._markdown_worker = None
        document = self._editor.document()
        if getattr(document, '_markdown_outline_pending', None) is worker:
            document._markdown_outline_pending = None
        if error:
            logger.error('Markdown outline parsing failed: %s', error)
            return
        if worker.revision == document.revision():
            document._markdown_outline = (worker.revision, symbols)
            if self._markdown_active and self.get_language().lower() == 'markdown':
                self.update_outline_info(symbols)
        elif self._markdown_active:
            self.request_symbols()

    def stop_requests(self):
        """Disconnect local work when the editor closes or changes language."""
        self._markdown_active = False
        if self._markdown_timer is not None:
            self._editor.textChanged.disconnect(self._schedule_markdown)
            self._markdown_timer.stop()
            self._markdown_timer.deleteLater()
            self._markdown_timer = None
        if self._markdown_worker is not None:
            self._markdown_worker.sig_finished.disconnect(self._markdown_finished)
            self._markdown_worker = None

    @property
    def is_cloned(self):
        """Check if the associated editor is cloned."""
        return self._editor.is_cloned

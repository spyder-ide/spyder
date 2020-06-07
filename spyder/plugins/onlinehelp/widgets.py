# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""pydoc widget"""

# Standard library imports
import os.path as osp
import pydoc
import sys

# Third party imports
from qtpy.QtCore import Qt, QThread, QUrl, Signal
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.config.base import _
from spyder.plugins.onlinehelp.pydoc_patch import (
    _start_server, _url_handler)
from spyder.py3compat import PY3, to_text_string
from spyder.utils.misc import select_port
from spyder.widgets.browser import WebBrowser


# =============================================================================
# Pydoc adjustments
# =============================================================================
# This is needed to prevent pydoc raise an ErrorDuringImport when
# trying to import numpy.
# See spyder-ide/spyder#10740
DIRECT_PYDOC_IMPORT_MODULES = ['numpy', 'numpy.core']
try:
    from pydoc import safeimport

    def spyder_safeimport(path, forceload=0, cache={}):
        if path in DIRECT_PYDOC_IMPORT_MODULES:
            forceload = 0
        return safeimport(path, forceload=forceload, cache=cache)

    pydoc.safeimport = spyder_safeimport
except Exception:
    pass


class PydocServer(QThread):
    """Pydoc server"""
    server_started = Signal()

    def __init__(self, port=7464):
        QThread.__init__(self)
        self.port = port
        self.server = None
        self.complete = False
        self.closed = False

    def run(self):
        if PY3:
            # Python 3
            self.callback(_start_server(_url_handler,
                                        hostname='127.0.0.1',
                                        port=self.port))
        else:
            # Python 2
            pydoc.serve(self.port, self.callback, self.completer)

    def callback(self, server):
        self.server = server
        if self.closed:
            self.quit_server()
        else:
            self.server_started.emit()

    def completer(self):
        self.complete = True

    def is_running(self):
        """Check if the server is running"""
        if PY3:
            if self.isRunning():
                # Startup
                return True
            if self.server is None:
                return False
            return self.server.serving
        else:
            # Py 2
            return self.isRunning()

    def quit_server(self):
        self.closed = True
        if self.server is None:
            return
        if PY3:
            # Python 3
            if self.server.serving:
                self.server.stop()
        else:
            # Python 2
            if self.isRunning():
                self.server.quit = 1


class PydocBrowser(WebBrowser):
    """
    pydoc widget
    """
    DEFAULT_PORT = 30128

    def __init__(self, parent, options_button=None, handle_links=False):
        WebBrowser.__init__(self, parent, options_button=options_button,
                            handle_links=handle_links)
        self.server = None
        self.port = None
        self.url_combo.lineEdit().setPlaceholderText(
            _('Write a package name here, e.g. pandas'))

    def initialize(self):
        """Start pydoc server"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QApplication.processEvents()
        self.start_server()
        # Initializing continues in `initialize_continued` method...

    def initialize_continued(self):
        """Load home page"""
        self.go_home()
        QApplication.restoreOverrideCursor()

    def closeEvent(self, event):
        """Handle close event"""
        self.quit_server()
        event.accept()

    # ------ Public API -------------------------------------------------------
    def start_server(self):
        """Start pydoc server"""
        if self.server is None:
            self.port = select_port(default_port=self.DEFAULT_PORT)
            self.set_home_url('http://127.0.0.1:%d/' % self.port)
        elif self.server.is_running():
            self.quit_server()
        self.server = PydocServer(port=self.port)
        self.server.server_started.connect(self.initialize_continued)
        self.server.start()

    def quit_server(self):
        """Quit the server"""
        if self.server is None:
            return
        if self.server.is_running():
            self.server.server_started.disconnect(self.initialize_continued)
            self.server.quit_server()
            self.server.quit()

    # ------ WebBrowser API ---------------------------------------------------
    def get_label(self):
        """Return address label text"""
        return _("Package:")

    def reload(self):
        """Reload page"""
        self.start_server()
        self.webview.reload()

    def load_finished(self, ok):
        """Handle load finished."""
        pass

    def text_to_url(self, text):
        """Convert text address into QUrl object"""
        if text != 'about:blank':
            text += '.html'
        if text.startswith('/'):
            text = text[1:]

        return QUrl(self.home_url.toString() + text)

    def url_to_text(self, url):
        """Convert QUrl object to displayed text in combo box"""
        string_url = url.toString()
        if 'about:blank' in string_url:
            return 'about:blank'
        elif 'get?key=' in string_url or 'search?key=' in string_url:
            return ''
        return osp.splitext(to_text_string(url.path()))[0][1:]


def test():
    """Run web browser"""
    from spyder.utils.qthelpers import qapplication
    app = qapplication(test_time=8)
    widget = PydocBrowser(None)
    widget.show()
    widget.initialize()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()

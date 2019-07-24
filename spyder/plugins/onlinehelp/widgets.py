# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""pydoc widget"""

# Standard library imports
import os.path as osp
import sys

# Third party imports
from qtpy.QtCore import Qt, QThread, QUrl, Signal
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.config.base import _
from spyder.py3compat import PY3, to_text_string
from spyder.utils.misc import select_port
from spyder.widgets.browser import WebBrowser


class PydocServer(QThread):
    """Pydoc server"""
    server_started = Signal()

    def __init__(self, port=7464):
        QThread.__init__(self)
        self.port = port
        self.server = None
        self.complete = False

    def run(self):
        import pydoc
        if PY3:
            # Python 3
            try:
                self.callback(pydoc._start_server(pydoc._url_handler,
                                                  port=self.port))
            except TypeError:
                # Python 3.7
                self.callback(pydoc._start_server(pydoc._url_handler,
                                                  hostname='localhost',
                                                  port=self.port))
        else:
            # Python 2
            pydoc.serve(self.port, self.callback, self.completer)

    def callback(self, server):
        self.server = server
        self.server_started.emit()

    def completer(self):
        self.complete = True

    def quit_server(self):
        if PY3:
            # Python 3
            if self.is_server_running() and self.server.serving:
                self.server.stop()
        else:
            # Python 2
            if self.is_server_running():
                self.server.quit = 1


class PydocBrowser(WebBrowser):
    """
    pydoc widget
    """
    DEFAULT_PORT = 30128

    def __init__(self, parent, options_button=None):
        WebBrowser.__init__(self, parent, options_button=options_button)
        self.server = None
        self.port = None

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

    def is_server_running(self):
        """Return True if pydoc server is already running"""
        return self.server is not None

    def closeEvent(self, event):
        if self.is_server_running():
            self.server.quit_server()
#        while not self.server.complete: #XXX Is it really necessary?
#            pass
        event.accept()

    #------ Public API -----------------------------------------------------
    def start_server(self):
        """Start pydoc server"""
        if self.server is None:
            self.port = select_port(default_port=self.DEFAULT_PORT)
            self.set_home_url('http://localhost:%d/' % self.port)
        elif self.server.isRunning():
            self.server.server_started.disconnect(self.initialize_continued)
            self.server.quit()
        self.server = PydocServer(port=self.port)
        self.server.server_started.connect(self.initialize_continued)
        self.server.start()

    #------ WebBrowser API -----------------------------------------------------
    def get_label(self):
        """Return address label text"""
        return _("Module or package:")

    def reload(self):
        """Reload page"""
        self.start_server()
        WebBrowser.reload(self)

    def text_to_url(self, text):
        """Convert text address into QUrl object"""
        if text.startswith('/'):
            text = text[1:]
        return QUrl(self.home_url.toString()+text+'.html')

    def url_to_text(self, url):
        """Convert QUrl object to displayed text in combo box"""
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

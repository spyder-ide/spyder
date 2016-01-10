# -*- coding: utf-8 -*-
#
# Copyright © 2016 The Spyder development team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

import socket
import errno
import os
import sys

# Local imports
from spyderlib.utils.misc import select_port
from spyderlib.utils.bsdsocket import read_packet, write_packet
from spyderlib.qt.QtCore import QThread, QProcess, Signal, QObject


class PluginClient(QObject):

    """
    A class which handles a connection to a plugin through a QProcess.
    """

    # Emitted when the plugin has initialized.
    initialized = Signal()

    # Emitted when the plugin has failed to load.
    errored = Signal()

    # Emitted when a request response is received.
    request_handled = Signal(object)

    def __init__(self, plugin_name):
        super(PluginClient, self).__init__()
        self.plugin_name = plugin_name
        self.start()

    def start(self):
        """Start a new connection with the plugin.
        """
        self._initialized = False
        plugin_name = self.plugin_name
        server_port = select_port()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", server_port))

        self.client_port = select_port()

        self.process = QProcess(self)
        self.process.setWorkingDirectory(os.path.dirname(__file__))
        p_args = ['plugin_server.py', str(self.client_port),
                  str(server_port), plugin_name]
        self.listener = PluginListener(sock)
        self.listener.request_handled.connect(self.request_handled.emit)
        self.listener.initialized.connect(self._on_initialized)
        self.listener.start()

        self.process.start(sys.executable, p_args)
        self.process.finished.connect(self._on_finished)
        running = self.process.waitForStarted()
        if not running:
            raise IOError('Could not start plugin %s' % plugin_name)

    def send(self, request):
        """Send a request to the plugin.
        """
        if not self._initialized:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", self.client_port))
        write_packet(sock, request)
        sock.close()

    def _on_initialized(self):
        self._initialized = True
        self.initialized.emit()

    def _on_finished(self):
        if self._initialized:
            self.start()
        else:
            self._initialized = False
            self.errored.emit()


class PluginListener(QThread):

    """A plugin response listener.
    """

    # Emitted when the plugin has intitialized.
    initialized = Signal()

    # Emitted when a request response has been received.
    request_handled = Signal(object)

    def __init__(self, sock):
        super(PluginListener, self).__init__()
        self.sock = sock
        self._initialized = False

    def run(self):
        while True:
            self.sock.listen(2)
            try:
                conn, _addr = self.sock.accept()
            except socket.error as e:
                # See Issue 1275 for details on why errno EINTR is
                # silently ignored here.
                eintr = errno.WSAEINTR if os.name == 'nt' else errno.EINTR
                if e.args[0] == eintr:
                    continue
                raise
            if not self._initialized:
                if read_packet(conn) == 'initialized':
                    self._initialized = True
                    self.initialized.emit()
            else:
                self.request_handled.emit(read_packet(conn))


if __name__ == '__main__':
    from spyderlib.qt.QtGui import QApplication
    app = QApplication(sys.argv)
    plugin = PluginClient('jedi')

    def handle_return(value):
        print(value)
        if value['method'] == 'foo':
            app.quit()
        else:
            plugin.send(dict(method='foo'))

    def handle_errored():
        print('errored')
        sys.exit(1)

    def start():
        plugin.send(dict(method='validate'))

    plugin.errored.connect(handle_errored)

    plugin.request_handled.connect(handle_return)
    plugin.initialized.connect(start)

    app.exec_()

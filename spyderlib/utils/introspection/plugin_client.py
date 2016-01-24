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
from spyderlib.config.base import debug_print
from spyderlib.utils.bsdsocket import read_packet, write_packet
from spyderlib.qt.QtGui import QApplication
from spyderlib.qt.QtCore import QThread, QProcess, Signal, QObject
from spyderlib.utils.introspection.utils import connect_to_port


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

    def __init__(self, plugin_name, executable=None):
        super(PluginClient, self).__init__()
        self.plugin_name = plugin_name
        self.executable = executable or sys.executable
        self.start()

    def start(self):
        """Start a new connection with the plugin.
        """
        self._initialized = False
        plugin_name = self.plugin_name
        self.sock, server_port = connect_to_port()
        self.sock.listen(2)
        QApplication.instance().aboutToQuit.connect(self.close)

        self.process = QProcess(self)
        self.process.setWorkingDirectory(os.path.dirname(__file__))
        p_args = ['plugin_server.py', str(server_port), plugin_name]

        self.listener = PluginListener(self.sock)
        self.listener.request_handled.connect(self.request_handled.emit)
        self.listener.initialized.connect(self._on_initialized)
        self.listener.start()

        self.process.start(self.executable, p_args)
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
        request['plugin_name'] = self.plugin_name
        write_packet(sock, request)
        sock.close()

    def close(self):
        self.process.kill()
        self.process.waitForFinished(200)
        self.sock.close()

    def _on_initialized(self, port):
        debug_print('Initialized %s' % self.plugin_name)
        self._initialized = True
        self.client_port = port
        self.initialized.emit()

    def _on_finished(self):
        debug_print('finished %s %s' % (self.plugin_name, self._initialized))
        if self._initialized:
            self.start()
        else:
            self._initialized = False
            self.errored.emit()


class PluginListener(QThread):

    """A plugin response listener.
    """

    # Emitted when the plugin has intitialized.
    initialized = Signal(int)

    # Emitted when a request response has been received.
    request_handled = Signal(object)

    def __init__(self, sock):
        super(PluginListener, self).__init__()
        self.sock = sock
        self._initialized = False

    def run(self):
        while True:
            try:
                conn, _addr = self.sock.accept()
            except socket.error as e:
                if e.args[0] in [errno.ECONNABORTED, errno.EBADFD]:
                    return
                # See Issue 1275 for details on why errno EINTR is
                # silently ignored here.
                eintr = errno.WSAEINTR if os.name == 'nt' else errno.EINTR
                if e.args[0] == eintr:
                    continue
                raise
            if not self._initialized:
                server_port = read_packet(conn)
                if isinstance(server_port, int):
                    self._initialized = True
                    self.initialized.emit(server_port)
            else:
                self.request_handled.emit(read_packet(conn))


if __name__ == '__main__':
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
        print('start')
        plugin.send(dict(method='validate'))

    plugin.errored.connect(handle_errored)

    plugin.request_handled.connect(handle_return)
    plugin.initialized.connect(start)

    app.exec_()

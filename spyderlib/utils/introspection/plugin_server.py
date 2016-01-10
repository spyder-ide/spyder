# -*- coding: utf-8 -*-
#
# Copyright © 2016 The Spyder development team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

import threading
import socket
import errno
import os
import sys

# Local imports
from spyderlib.py3compat import Queue
from spyderlib.utils.bsdsocket import read_packet, write_packet


class PluginServer(object):

    """
    Introspection plugin server, provides a separate process
    for interacting with the plugin.
    """

    def __init__(self, server_port, client_port, plugin_name):
        mod_name = plugin_name + '_plugin'
        mod = __import__('spyderlib.utils.introspection.' + mod_name,
                         fromlist=[mod_name])
        cls = getattr(mod, '%sPlugin' % plugin_name.capitalize())
        plugin = cls()
        plugin.load_plugin()
        self.plugin = plugin

        self._client_port = int(client_port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", int(server_port)))
        self._server_sock = sock

        self.queue = Queue.Queue()
        self._listener = threading.Thread(target=self.listen)
        self._listener.setDaemon(True)
        self._listener.start()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", self._client_port))
        write_packet(sock, 'initialized')
        sock.close()

    def listen(self):
        """Listen for requests"""
        while True:
            self._server_sock.listen(2)
            try:
                conn, _addr = self._server_sock.accept()
            except socket.error as e:
                # See Issue 1275 for details on why errno EINTR is
                # silently ignored here.
                eintr = errno.WSAEINTR if os.name == 'nt' else errno.EINTR
                if e.args[0] == eintr:
                    continue
                raise
            self.queue.put(read_packet(conn))

    def run(self):
        """Handle requests"""
        while 1:
            # Get most recent request
            request = None
            while 1:
                try:
                    request = self.queue.get(True, 0.005)
                except Queue.Empty:
                    break
            if request is None:
                continue
            try:
                method = getattr(self.plugin, request['method'])
                args = request.get('args', [])
                kwargs = request.get('kwargs', {})
                request['response'] = method(*args, **kwargs)
            except Exception as e:
                request['error'] = str(e)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", self._client_port))
            write_packet(sock, request)
            sock.close()


if __name__ == '__main__':
    args = sys.argv[1:]
    if not len(args) == 3:
        print('Usage: plugin_server.py server_port client_port plugin_name')
        sys.exit(0)
    plugin = PluginServer(*args)
    print('Started')
    plugin.run()

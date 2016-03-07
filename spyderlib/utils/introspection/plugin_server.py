# -*- coding: utf-8 -*-
#
# Copyright © 2016 The Spyder development team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

import sys
import traceback

import zmq


# Timeout in milliseconds
TIMEOUT = 10000


class AsyncServer(object):

    """
    Introspection server, provides a separate process
    for interacting with an object.
    """

    def __init__(self, port, *args):
        self.port = port
        self.object = self.initialize(*args)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PAIR)
        self.socket.connect("tcp://localhost:%s" % port)
        self.socket.send_pyobj(port)

    def initialize(self, plugin_name):
        """Initialize the object and return it.
        """
        return object()

    def run(self):
        """Handle requests from the client.
        """
        while 1:
            events = self.socket.poll(TIMEOUT)
            if events == 0:
                print('Timed out')
                return
            request = self.socket.recv_pyobj()
            if request['func_name'] == 'server_quit':
                print('Quitting')
                sys.stdout.flush()
                return
            try:
                func = getattr(self.object, request['func_name'])
                args = request.get('args', [])
                kwargs = request.get('kwargs', {})
                request['result'] = func(*args, **kwargs)
            except Exception:
                request['error'] = traceback.format_exc()
            self.socket.send_pyobj(request)


class PluginServer(AsyncServer):

    """
    Introspection plugin server, provides a separate process
    for interacting with a plugin.
    """

    def initialize(self, plugin_name):
        """Initialize the object and return it.
        """
        mod_name = plugin_name + '_plugin'
        mod = __import__('spyderlib.utils.introspection.' + mod_name,
                         fromlist=[mod_name])
        cls = getattr(mod, '%sPlugin' % plugin_name.capitalize())
        plugin = cls()
        plugin.load_plugin()
        return plugin


if __name__ == '__main__':
    args = sys.argv[1:]
    if not len(args) == 2:
        print('Usage: plugin_server.py client_port plugin_name')
        sys.exit(0)
    plugin = PluginServer(*args)
    print('Started')
    plugin.run()

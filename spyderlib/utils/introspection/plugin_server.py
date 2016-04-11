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
            # Poll for events, handling a timeout.
            events = self.socket.poll(TIMEOUT)
            if events == 0:
                print('Timed out')
                return
            # Drain all exising requests, handling quit and heartbeat.
            requests = []
            while 1:
                request = self.socket.recv_pyobj()
                if request['func_name'] == 'server_quit':
                    print('Quitting')
                    sys.stdout.flush()
                    return
                elif request['func_name'] != 'server_heartbeat':
                    requests.append(request)
                events = self.socket.poll(0)
                if events == 0:
                    break
            # Select the most recent request.
            if not requests:
                continue
            request = requests[-1]

            # Gather the response
            response = dict(func_name=request['func_name'],
                            request_id=request['request_id'])
            try:
                func = getattr(self.object, request['func_name'])
                args = request.get('args', [])
                kwargs = request.get('kwargs', {})
                response['result'] = func(*args, **kwargs)
            except Exception:
                response['error'] = traceback.format_exc()

            # Send the response to the client.
            self.socket.send_pyobj(response)


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

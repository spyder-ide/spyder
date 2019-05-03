# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


"""
Spyder MS Language Server Protocol v3.0 transport proxy base implementation.

This module provides the base class from which each transport-specific client
should inherit from. LanguageServerClient implements functions to handle
incoming requests from the actual Spyder LSP client ZMQ queue and to
encapsulate them into valid JSONRPC messages before sending them to the
LSP server, using the specific transport mode.
"""

# Standard library imports
import json
import logging

# Third party imports
import zmq

TIMEOUT = 5000

logger = logging.getLogger(__name__)


class LanguageServerClient(object):
    """Base implementation of a v3.0 compilant language server client."""
    CONTENT_LENGTH = 'Content-Length: {0}\r\n\r\n'

    def __init__(self, zmq_in_port=7000, zmq_out_port=7001):
        self.zmq_in_port = zmq_in_port
        self.zmq_out_port = zmq_out_port
        self.context = None
        self.zmq_in_socket = None
        self.zmq_out_socket = None

    def finalize_initialization(self):
        connected, connection_error = self.is_server_alive()

        if not connected:
            logger.error("The client was unable to establish a connection "
                         "with the Language Server. The error was: "
                         "{}".format(connection_error))
            raise Exception("An error occurred while trying to create a "
                            "client to connect to the Language Server! The "
                            "error was\n\n{}".format(connection_error))

        logger.info('Starting ZMQ connection...')
        self.context = zmq.Context()
        self.zmq_in_socket = self.context.socket(zmq.PAIR)
        self.zmq_in_socket.connect("tcp://localhost:{0}".format(
            self.zmq_in_port))
        self.zmq_out_socket = self.context.socket(zmq.PAIR)
        self.zmq_out_socket.connect("tcp://localhost:{0}".format(
            self.zmq_out_port))
        logger.info('Sending server_ready...')
        self.zmq_out_socket.send_pyobj({'id': -1, 'method': 'server_ready',
                                        'params': {}})

    def listen(self):
        events = self.zmq_in_socket.poll(TIMEOUT)
        # requests = []
        while events > 0:
            client_request = self.zmq_in_socket.recv_pyobj()
            logger.debug("Client Event: {0}".format(client_request))
            server_request = self.__compose_request(client_request['id'],
                                                    client_request['method'],
                                                    client_request['params'])
            self.__send_request(server_request)
            # self.zmq_socket.send_pyobj({'a': 'b'})
            events -= 1

    def __compose_request(self, id, method, params):
        request = {
            "jsonrpc": "2.0",
            "id": id,
            "method": method,
            "params": params
        }
        return request

    def __send_request(self, request):
        json_req = json.dumps(request)
        content = bytes(json_req.encode('utf-8'))
        content_length = len(content)

        logger.debug('Sending request of type: {0}'.format(request['method']))
        logger.debug(json_req)

        content_length = self.CONTENT_LENGTH.format(
            content_length).encode('utf-8')
        self.transport_send(bytes(content_length), content)

    def transport_send(self, content_length, body):
        """Subclasses should override this method"""
        raise NotImplementedError("Not implemented")

    def is_server_alive(self):
        """Subclasses should override this method"""
        raise NotImplementedError("Not implemented")

    def start(self):
        """Subclasses should override this method."""
        raise NotImplementedError("Not implemented")

    def stop(self):
        """Subclasses should override this method."""
        raise NotImplementedError("Not implemented")

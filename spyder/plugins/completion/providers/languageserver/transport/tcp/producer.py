# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


"""
Spyder MS Language Server Protocol v3.0 transport proxy implementation.

This module handles incoming requests from the actual Spyder LSP client ZMQ
queue, encapsulates them into valid JSONRPC messages and sends them to a
LSP server via TCP.
"""

# Standard library imports
import logging
import socket
import time

# Local imports
from spyder.plugins.completion.providers.languageserver.transport.tcp.consumer import (
    TCPIncomingMessageThread)
from spyder.plugins.completion.providers.languageserver.transport.common.producer import (
    LanguageServerClient)
from spyder.py3compat import ConnectionError, BrokenPipeError


logger = logging.getLogger(__name__)


class TCPLanguageServerClient(LanguageServerClient):
    """Implementation of a v3.0 compilant language server TCP client."""
    MAX_TIMEOUT_TIME = 20000

    def __init__(self, host='127.0.0.1', port=2087, zmq_in_port=7000,
                 zmq_out_port=7001):
        LanguageServerClient.__init__(self, zmq_in_port, zmq_out_port)
        self.req_status = {}
        self.host = host
        self.port = port
        self.socket = None
        # self.request_seq = 1
        logger.info('Connecting to language server at {0}:{1}'.format(
            self.host, self.port))
        super(TCPLanguageServerClient, self).finalize_initialization()
        self.socket.setblocking(True)
        self.reading_thread = TCPIncomingMessageThread()
        self.reading_thread.initialize(self.socket, self.zmq_out_socket,
                                       self.req_status)

    def start(self):
        self.reading_thread.start()
        logger.info('Ready to receive/attend requests and responses!')

    def stop(self):
        logger.info('Closing TCP socket...')
        self.socket.close()
        logger.info('Closing consumer thread...')
        self.reading_thread.stop()
        logger.debug('Exit routine should be complete')

    def transport_send(self, content_length, body):
        logger.debug('Sending message via TCP')
        try:
            self.socket.send(content_length)
            self.socket.send(body)
        except (BrokenPipeError, ConnectionError) as e:
            # This avoids a total freeze at startup
            # when we're trying to connect to a TCP
            # socket that rejects our connection
            logger.error(e)

    def is_server_alive(self):
        connected = False
        initial_time = time.time()
        connection_error = None
        while not connected:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, int(self.port)))
                connected = True
            except Exception as e:
                connection_error = e

            if time.time() - initial_time > self.MAX_TIMEOUT_TIME:
                break
        return connected, connection_error, None

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
LSP server via stdio pipes.
"""

# Standard library imports
import logging
import sys

# Local imports
from spyder.plugins.editor.lsp.transport.stdio.consumer import (
    StdioIncomingMessageThread)
from spyder.plugins.editor.lsp.transport.common import LanguageServerClient

logger = logging.getLogger(__name__)


class StdioLanguageServerClient(LanguageServerClient):
    """Implementation of a v3.0 compilant language server stdio client."""

    def __init__(self, zmq_in_port=7000, zmq_out_port=7001):
        super(StdioLanguageServerClient, self).__init__(
            zmq_in_port, zmq_out_port)
        self.req_status = {}
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        # self.request_seq = 1
        logger.info('Connecting to language server on stdio')
        super(StdioLanguageServerClient, self).finalize_initialization()
        self.reading_thread = StdioIncomingMessageThread()
        self.reading_thread.initialize(self.stdin.buffer, self.zmq_out_socket,
                                       self.req_status)
        self.stdout.buffer.write(b'0')
        self.stdout.buffer.write(b'0')
        self.stdout.buffer.write(b'0')
        self.stdout.buffer.write(b'0')

    def start(self):
        self.reading_thread.start()
        logger.info('Ready to receive/attend requests and responses!')

    def stop(self):
        logger.info('Closing consumer thread...')
        self.reading_thread.stop()
        logger.debug('Joining thread...')
        self.reading_thread.join()
        logger.debug('Exit routine should be complete')

    def transport_send(self, content_length, body):
        self.stdout.buffer.write(content_length)
        self.stdout.buffer.write(body)

    def is_server_alive(self):
        """This method verifies if stdout is broken."""
        connected = False
        connection_error = None
        try:
            self.stdout.buffer.write(b'0')
            connected = True
        except Exception as e:
            connection_error = e
        return connected, connection_error

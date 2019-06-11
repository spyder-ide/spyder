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
import os
import time
import logging

# Local imports
from spyder.plugins.editor.lsp.transport.stdio.consumer import (
    StdioIncomingMessageThread)
from spyder.plugins.editor.lsp.transport.common.producer import (
    LanguageServerClient)

from pexpect import popen_spawn

logger = logging.getLogger(__name__)


class StdioLanguageServerClient(LanguageServerClient):
    """Implementation of a v3.0 compilant language server stdio client."""
    MAX_TIMEOUT_TIME = 20000

    def __init__(self, server_args='', log_file='',
                 zmq_in_port=7000, zmq_out_port=7001):
        super(StdioLanguageServerClient, self).__init__(
            zmq_in_port, zmq_out_port)
        self.req_status = {}
        self.process = None
        logger.debug(server_args)
        logger.debug('Redirect stderr to {0}'.format(log_file))
        self.process = popen_spawn.PopenSpawn(server_args)
        logger.info('Connecting to language server on stdio')
        super(StdioLanguageServerClient, self).finalize_initialization()
        self.reading_thread = StdioIncomingMessageThread()
        self.reading_thread.initialize(self.process, self.zmq_out_socket,
                                       self.req_status, expectable=True)

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
        if os.name == 'nt':
            content_length = content_length.decode('utf-8')
            body = body.decode('utf-8')
        self.process.write(content_length)
        self.process.write(body)

    def is_server_alive(self):
        """This method verifies if stdout is broken."""
        connected = False
        connection_error = None
        initial_time = time.time()
        try:
            while not connected:
                connected = not self.process.proc.poll()
                if time.time() - initial_time > self.MAX_TIMEOUT_TIME:
                    connection_error = 'Timeout communication period exceeded'
                    break
        except Exception as e:
            connection_error = e
        return connected, connection_error

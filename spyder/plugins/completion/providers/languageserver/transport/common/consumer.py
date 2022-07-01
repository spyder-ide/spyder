# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


"""
Spyder MS Language Server Protocol v3.0 base transport proxy implementation.

This module handles and processes incoming messages sent by an LSP server,
then it relays the information to the actual Spyder LSP client via ZMQ.
"""


import os
import json
import socket
import logging
from threading import Thread, Lock

if not os.name == 'nt':
    from pexpect.fdpexpect import fdspawn


TIMEOUT = 5000
PID = os.getpid()


logger = logging.getLogger(__name__)


class IncomingMessageThread(Thread):
    """Base LSP message consumer."""

    def __init__(self):
        Thread.__init__(self)
        self.stopped = False
        self.daemon = True
        self.expect_body = False
        self.mutex = Lock()

    def initialize(self, fd, zmq_sock, req_status, expectable=False):
        self.fd = fd
        self.expect = None
        self.expectable = expectable
        logger.info('Reading thread initialized')
        self.read_incoming = self.read_posix
        self.expect = self.fd
        if not expectable:
            if os.name == 'nt':
                self.read_incoming = self.expect_windows
            else:
                self.expect = fdspawn(self.fd)
        self.zmq_sock = zmq_sock
        self.req_status = req_status

    def read_posix(self):
        self.expect.expect('\r\n\r\n', timeout=None)
        headers = self.expect.before
        headers = self.parse_headers(headers)
        logger.debug(headers)
        content_length = int(headers[b'Content-Length'])
        body = self.expect.read(size=content_length)
        return self.encode_body(body, headers)

    def encode_body(self, body, headers):
        encoding = 'utf8'
        if b'Content-Type' in headers:
            encoding = headers[b'Content-Type'].split(b'=')[-1].decode('utf8')
        body = body.decode(encoding)
        return body

    def expect_windows(self):
        buffer = b''
        headers = b''
        continue_reading = True
        while continue_reading:
            try:
                buffer += self.read_num_bytes(1)
                if b'\r\n\r\n' in buffer:
                    split = buffer.split(b'\r\n\r\n')
                    if len(split) == 2:
                        headers, buffer = split
                        continue_reading = False
            except socket.error as e:
                logger.error(e)
                raise e
        headers = self.parse_headers(headers)
        logger.debug(headers)
        content_length = int(headers[b'Content-Length'])
        pending_bytes = content_length - len(buffer)
        while pending_bytes > 0:
            logger.debug('Pending bytes...' + str(pending_bytes))
            recv = self.read_num_bytes(min(1024, pending_bytes))
            buffer += recv
            pending_bytes -= len(recv)
        return self.encode_body(buffer, headers)

    def run(self):
        while True:
            with self.mutex:
                if self.stopped:
                    logger.debug('Stopping Thread...')
                    break
            try:
                body = self.read_incoming()
                err = False
                try:
                    body = json.loads(body)
                except (ValueError, TypeError) as e:
                    err = True
                    logger.error(e)
                if not err:
                    logger.debug(body)
                    self.zmq_sock.send_pyobj(body)
                    logger.debug('Message sent')
            except socket.error as e:
                logger.error(e)
        logger.debug('Thread stopped.')

    def parse_headers(self, headers):
        logger.debug('Headers: {0}'.format(headers))
        headers = headers.split(b'\r\n')
        header_dict = dict([x.split(b': ') for x in headers])
        return header_dict

    def stop(self):
        with self.mutex:
            self.stopped = True

    def read_num_bytes(self, n):
        """Subclasses should override this method"""
        return NotImplementedError("Not implemented")

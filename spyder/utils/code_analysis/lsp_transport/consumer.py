# -*- coding: utf-8 -*-

"""
Spyder MS Language Server Protocol v3.0 transport proxy implementation.

This module handles and processes incoming TCP messages sent by
a lsp-server, then it relays the information to the actual Spyder lsp
client via ZMQ.
"""


import os
import json
import socket
import logging
from threading import Thread, Lock
from pexpect.fdpexpect import fdspawn


TIMEOUT = 5000
PID = os.getpid()
WINDOWS = os.name == 'nt'

LOGGER = logging.getLogger(__name__)


class IncomingMessageThread(Thread):
    """TCP socket consumer."""
    CHUNK_BYTE_SIZE = 4096

    def __init__(self):
        Thread.__init__(self)
        self.stopped = False
        self.expect_body = False
        self.mutex = Lock()

    def initialize(self, sock, zmq_sock, req_status):
        self.socket = sock
        self.expect = fdspawn(self.socket)
        self.zmq_sock = zmq_sock
        self.req_status = req_status

    def run(self):
        while True:
            with self.mutex:
                if self.stopped:
                    LOGGER.debug('Stopping Thread...')
                    break
            try:
                self.expect.expect('\r\n\r\n', timeout=None)
                headers = self.expect.before
                headers = self.parse_headers(headers)
                LOGGER.debug(headers)
                content_length = int(headers[b'Content-Length'])
                # recv = self.socket.recv(content_length)
                # LOGGER.debug(recv)
                body = self.expect.read(size=content_length)
                err = False
                try:
                    body = json.loads(body)
                except ValueError:
                    err = True
                # recv = self.socket.recv(self.CHUNK_BYTE_SIZE)
                # LOGGER.debug(body)
                # err, body = self.process_response(recv)
                # LOGGER.debug(body)
                if not err:
                    LOGGER.debug(body)
                    self.zmq_sock.send_pyobj(body)
                    LOGGER.debug('Message sent')
            except socket.error:
                pass
        LOGGER.debug('Thread stopped.')

    def parse_headers(self, headers):
        LOGGER.debug(headers)
        headers = headers.split(b'\r\n')
        header_dict = dict([x.split(b': ') for x in headers])
        return header_dict

    def stop(self):
        with self.mutex:
            self.stopped = True

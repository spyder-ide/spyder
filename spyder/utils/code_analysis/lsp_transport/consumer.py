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
        self.daemon = True
        self.expect_body = False
        self.mutex = Lock()

    def initialize(self, sock, zmq_sock, req_status):
        self.socket = sock
        self.expect = None
        self.read_sock = self.expect_windows
        if not WINDOWS:
            self.read_sock = self.read_posix
            self.expect = fdspawn(self.socket)
        self.zmq_sock = zmq_sock
        self.req_status = req_status


    def read_posix(self):
        self.expect.expect('\r\n\r\n', timeout=None)
        headers = self.expect.before
        headers = self.parse_headers(headers)
        LOGGER.debug(headers)
        content_length = int(headers[b'Content-Length'])
        body = self.expect.read(size=content_length)
        return body


    def expect_windows(self):
        buffer = b''
        headers = b''
        continue_reading = True
        while continue_reading:
            try:
                buffer += self.socket.recv(1024)
                if b'\r\n\r\n' in buffer:
                    split = buffer.split(b'\r\n\r\n')
                    if len(split) == 2:
                        headers, buffer = split
                        continue_reading = False
            except socket.error as e:
                LOGGER.error(e)
                raise e
        headers = self.parse_headers(headers)
        LOGGER.debug(headers)
        content_length = int(headers[b'Content-Length'])
        pending_bytes = content_length - len(buffer)
        while pending_bytes > 0:
            recv = self.socket.recv(min(1024, pending_bytes))
            buffer += recv
            pending_bytes -= len(recv)
        return buffer

    def run(self):
        while True:
            with self.mutex:
                if self.stopped:
                    LOGGER.debug('Stopping Thread...')
                    break
            try:
                body = self.read_sock()
                err = False
                try:
                    body = json.loads(body)
                except (ValueError, TypeError):
                    err = True
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

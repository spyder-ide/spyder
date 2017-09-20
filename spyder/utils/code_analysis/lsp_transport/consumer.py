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
        self.zmq_sock = zmq_sock
        self.req_status = req_status

    def run(self):
        while True:
            with self.mutex:
                if self.stopped:
                    LOGGER.debug('Stopping Thread...')
                    break
            try:
                recv = self.socket.recv(self.CHUNK_BYTE_SIZE)
                # LOGGER.debug(recv)
                err, body = self.process_response(recv)
                if not err and body is not None:
                    LOGGER.debug(body)
                    self.zmq_sock.send_pyobj(body)
                    LOGGER.debug('Message sent')
            except socket.error:
                pass
        LOGGER.debug('Thread stopped.')

    def process_response(self, response):
        err = True
        body = None
        response = str(response.decode('utf-8'))
        msg_parts = response.split('\r\n\r\n')
        if len(msg_parts) == 1:
            if self.expect_body:
                body = msg_parts[0]
                try:
                    body = json.loads(body)
                    err = False
                    self.expect_body = False
                except ValueError:
                    pass
        elif len(msg_parts) == 2:
            headers, body = msg_parts
            headers = headers.split('\r\n')
            content_length_header = next(
                (x for x in headers if x.startswith('Content-Length')))
            content_length = int(content_length_header.split(': ')[-1])
            if content_length > len(body.encode('utf-8')):
                remaining = content_length - len(body.encode('utf-8'))
                while remaining > 0:
                    recv = self.socket.recv(min(
                        self.CHUNK_BYTE_SIZE, remaining))
                    body += str(recv.decode('utf-8'))
                    remaining -= len(recv)
            if len(body) == 0:
                # headers = headers.split(';')
                if headers[0].startswith('Content-Length'):
                    self.expect_body = True
                    err = False
            else:
                try:
                    body = json.loads(body)
                    err = False
                    self.expect_body = False
                except ValueError:
                    pass
        if err:
            LOGGER.error('Invalid message recieved, discarding')

        return err, body

    def stop(self):
        with self.mutex:
            self.stopped = True

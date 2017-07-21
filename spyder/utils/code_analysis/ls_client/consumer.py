# -*- coding: utf-8 -*-

"""Spyder MS Language Server v3.0 client implementation."""


import os
import socket
import logging
from threading import Thread, Lock


TIMEOUT = 5000
PID = os.getpid()
WINDOWS = os.name == 'nt'

LOGGER = logging.getLogger(__name__)


class IncomingMessageThread(Thread):
    """TCP socket consumer."""

    def __init__(self):
        Thread.__init__(self)
        self.stopped = False
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
                recv = self.socket.recv(4096)
                LOGGER.debug(recv)
                self.zmq_sock.send_pyobj(recv)
            except socket.error:
                pass
        LOGGER.debug('Thread stopped.')

    def stop(self):
        with self.mutex:
            self.stopped = True

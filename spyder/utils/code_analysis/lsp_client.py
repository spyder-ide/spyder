# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder Language Server Protocol Client implementation.

This client implements the calls and procedures required to
communicate with a v3.0 Language Server Protocol server.
"""

import os
import sys
import zmq
import signal
import datetime
import subprocess
import os.path as osp
from spyder.config.base import DEV
from spyder.py3compat import getcwd
from spyder.utils.code_analysis import (CLIENT_CAPABILITES,
                                        SERVER_CAPABILITES, TRACE,
                                        LSPRequestTypes)
from spyder.utils.code_analysis.decorators import (send_request,
                                                   class_register)
from spyder.utils.code_analysis.lsp_providers import LSPMethodProviderMixIn

from qtpy.QtCore import QObject, Signal, QSocketNotifier
from qtpy.QtWidgets import QApplication

LOCATION = osp.realpath(osp.join(os.getcwd(),
                                 osp.dirname(__file__)))

PENDING = 'pending'


@class_register
class LSPClient(QObject, LSPMethodProviderMixIn):
    """Language Server Protocol v3.0 client implementation."""
    initialized = Signal()
    external_server_fmt = ('--server-host %(host)s '
                           '--server-port %(port)s '
                           '--external-server')
    local_server_fmt = ('--server-host %(host)s '
                        '--server-port %(port)s '
                        '--server %(server_cmd)s')

    def __init__(self, server_args_fmt='',
                 server_settings={}, external_server=False,
                 folder=getcwd()):
        QObject.__init__(self)
        # LSPMethodProviderMixIn.__init__(self)
        self.zmq_socket = None
        self.zmq_port = None
        self.transport_client = None

        self.initialized = False
        self.request_seq = 1
        self.req_status = {}
        QApplication.instance().aboutToQuit.connect(self.stop)

        self.transport_args = [sys.executable,
                               osp.join(LOCATION, 'lsp_transport', 'main.py')]
        self.external_server = external_server

        self.folder = folder
        self.client_capabilites = CLIENT_CAPABILITES
        self.server_capabilites = SERVER_CAPABILITES
        self.context = zmq.Context()

        server_args = server_args_fmt % (server_settings)
        transport_args = self.local_server_fmt % (server_settings)
        if self.external_server:
            transport_args = self.external_server_fmt % (server_settings)

        self.server_args = server_args.split(' ')
        self.transport_args += transport_args.split(' ')
        self.transport_args += ['--folder', folder]
        if DEV:
            self.transport_args.append('--transport-debug')

    def start(self):
        self.zmq_socket = self.context.socket(zmq.PAIR)
        self.port = self.socket.bind_to_random_port('tcp://*')
        self.transport_args += ['--zmq-port', self.port]

        if not self.external_server:
            self.transport_args += self.server_args

        self.stdout_log = subprocess.PIPE
        self.stderr_log = subprocess.PIPE
        if DEV:
            stdout_log_file = 'lsp_client_{0}_out.log'.format(
                datetime.datetime.now().isoformat())
            stderr_log_file = 'lsp_client_{0}_err.log'.format(
                datetime.datetime.now().isoformat())
            self.stdout_log = open(osp.join(getcwd(), stdout_log_file), 'w')
            self.stderr_log = open(osp.join(getcwd(), stderr_log_file), 'w')

        self.transport_client = subprocess.Popen(self.transport_args,
                                                 stdout=self.stdout_log,
                                                 stderr=self.stderr_log)

        fid = self.zmq_socket.getsockopt(zmq.FD)
        self.notifier = QSocketNotifier(fid, QSocketNotifier.Read, self)
        self.notifier.activated.connect(self.on_msg_received)

        self.initialize()

    def stop(self):
        self.shutdown()
        self.exit()
        if self.notifier is not None:
            self.notifier.activated.disconnect(self._on_msg_received)
            self.notifier.setEnabled(False)
            self.notifier = None
        self.transport_client.send_signal(signal.SIGINT)
        self.context.destroy()

    def send(self, method, params, requires_response):
        msg = {
            'id': self.request_seq,
            'method': method,
            'params': params
        }
        if requires_response:
            self.req_status[self.request_seq] = PENDING

        self.zmq_socket.send_pyobj(msg)
        self.request_seq += 1

    def on_msg_received(self):
        self.notifier.setEnabled(False)
        while True:
            try:
                resp = self.zmq_socket.recv_pyobj(flags=zmq.NOBLOCK)
            except zmq.ZMQError:
                self.notifier.setEnabled(True)
                break

    # ------ LSP initialization methods --------------------------------
    @send_request(method=LSPRequestTypes.INITIALIZE)
    def initialize(self):
        params = {
            'processId': self.transport_client.pid,
            'rootUri': self.folder,
            'capabilities': self.client_capabilites,
            'trace': TRACE
        }
        return params

    @send_request(method=LSPRequestTypes.SHUTDOWN, requires_response=False)
    def shutdown(self):
        params = {}
        return params

    @send_request(method=LSPRequestTypes.EXIT, requires_response=False)
    def exit(self):
        params = {}
        return params

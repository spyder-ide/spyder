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
# from spyder.config.base import DEV
from spyder.py3compat import PY2, getcwd
from spyder.config.base import debug_print
from spyder.utils.code_analysis import (CLIENT_CAPABILITES,
                                        SERVER_CAPABILITES, TRACE,
                                        TEXT_DOCUMENT_SYNC_OPTIONS,
                                        LSPRequestTypes,
                                        LSPEventTypes, ClientConstants)
from spyder.utils.code_analysis.decorators import (send_request,
                                                   class_register,
                                                   handles)
from spyder.utils.code_analysis.lsp_providers import LSPMethodProviderMixIn

from qtpy.QtCore import QObject, Signal, QSocketNotifier, Slot
# from qtpy.QtWidgets import QApplication

if PY2:
    import pathlib2 as pathlib
else:
    import pathlib


DEV = True

LOCATION = osp.realpath(osp.join(os.getcwd(),
                                 osp.dirname(__file__)))

PENDING = 'pending'
SERVER_READY = 'server_ready'

WINDOWS = os.name == 'nt'

@class_register
class LSPClient(QObject, LSPMethodProviderMixIn):
    """Language Server Protocol v3.0 client implementation."""
    initialized = Signal()
    external_server_fmt = ('--server-host %(host)s '
                           '--server-port %(port)s '
                           '--external-server')
    local_server_fmt = ('--server-host %(host)s '
                        '--server-port %(port)s '
                        '--server %(cmd)s')

    def __init__(self, parent, server_args_fmt='',
                 server_settings={}, external_server=False,
                 folder=getcwd(), language='python'):
        QObject.__init__(self)
        # LSPMethodProviderMixIn.__init__(self)
        self.manager = parent
        self.zmq_in_socket = None
        self.zmq_out_socket = None
        self.zmq_in_port = None
        self.zmq_out_port = None
        self.transport_client = None
        self.language = language

        self.initialized = False
        self.ready_to_close = False
        self.request_seq = 1
        self.req_status = {}
        self.plugin_registry = {}
        self.watched_files = {}
        self.req_reply = {}

        self.transport_args = [sys.executable, '-u',
                               osp.join(LOCATION, 'lsp_transport', 'main.py')]
        self.external_server = external_server

        self.folder = folder
        self.client_capabilites = CLIENT_CAPABILITES
        self.server_capabilites = SERVER_CAPABILITES
        self.context = zmq.Context()

        server_args = server_args_fmt % (server_settings)
        # transport_args = self.local_server_fmt % (server_settings)
        # if self.external_server:
        transport_args = self.external_server_fmt % (server_settings)

        self.server_args = [server_settings['cmd']]
        self.server_args += server_args.split(' ')
        self.transport_args += transport_args.split(' ')
        self.transport_args += ['--folder', folder]
        if DEV:
            self.transport_args.append('--transport-debug')

    def start(self):
        self.zmq_out_socket = self.context.socket(zmq.PAIR)
        self.zmq_out_port = self.zmq_out_socket.bind_to_random_port('tcp://*')
        self.zmq_in_socket = self.context.socket(zmq.PAIR)
        self.zmq_in_socket.set_hwm(0)
        self.zmq_in_port = self.zmq_in_socket.bind_to_random_port('tcp://*')
        self.transport_args += ['--zmq-in-port', self.zmq_out_port,
                                '--zmq-out-port', self.zmq_in_port]

        self.lsp_server_log = subprocess.PIPE
        if DEV:
            lsp_server_file = 'lsp_server_logfile.log'
            self.lsp_server_log = open(osp.join(
                getcwd(), lsp_server_file), 'w')

        if not self.external_server:
            debug_print('Starting server: {0}'.format(
                ' '.join(self.server_args)))
            creation_flags = 0
            if WINDOWS:
                creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
            self.lsp_server = subprocess.Popen(
                self.server_args,
                stdout=self.lsp_server_log,
                stderr=subprocess.STDOUT,
                creationflags=creation_flags)
            # self.transport_args += self.server_args

        self.stdout_log = subprocess.PIPE
        self.stderr_log = subprocess.PIPE
        if DEV:
            stdout_log_file = 'lsp_client_out.log'.format(
                datetime.datetime.now().isoformat())
            stderr_log_file = 'lsp_client_err.log'.format(
                datetime.datetime.now().isoformat())
            # self.stdout_log = open(osp.join(getcwd(), stdout_log_file), 'w')
            self.stderr_log = open(osp.join(getcwd(), stderr_log_file), 'w')

        new_env = dict(os.environ)
        python_path = os.pathsep.join(sys.path)[1:]
        new_env['PYTHONPATH'] = python_path
        self.transport_args = map(str, self.transport_args)
        self.transport_client = subprocess.Popen(self.transport_args,
                                                 stdout=self.stdout_log,
                                                 stderr=self.stderr_log,
                                                 env=new_env)

        fid = self.zmq_in_socket.getsockopt(zmq.FD)
        self.notifier = QSocketNotifier(fid, QSocketNotifier.Read, self)
        # self.notifier.activated.connect(self.debug_print)
        self.notifier.activated.connect(self.on_msg_received)
        # self.initialize()

    def stop(self):
        # self.shutdown()
        # self.exit()
        debug_print('LSP Client ==> Stopping...')
        if self.notifier is not None:
            self.notifier.activated.disconnect(self.on_msg_received)
            self.notifier.setEnabled(False)
            self.notifier = None
        if WINDOWS:
            self.transport_client.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            self.transport_client.kill()
        self.context.destroy()
        self.lsp_server.kill()

    def send(self, method, params, requires_response):
        if ClientConstants.CANCEL in params:
            return
        msg = {
            'id': self.request_seq,
            'method': method,
            'params': params
        }
        if requires_response:
            self.req_status[self.request_seq] = method

        debug_print('\n[{0}] LSP-Client ===>'.format(self.language))
        debug_print(method)
        # debug_print('')
        self.zmq_out_socket.send_pyobj(msg)
        self.request_seq += 1
        return int(msg['id'])

    @Slot()
    def on_msg_received(self):
        self.notifier.setEnabled(False)
        while True:
            try:
                # events = self.zmq_in_socket.poll(1500)
                resp = self.zmq_in_socket.recv_pyobj(flags=zmq.NOBLOCK)
                debug_print('\n[{0}] LSP-Client <==='.format(self.language))
                debug_print(resp)
                debug_print('')
                if 'method' in resp:
                    if resp['method'][0] != '$':
                        if resp['method'] in self.handler_registry:
                            handler_name = (
                                self.handler_registry[resp['method']])
                            handler = getattr(self, handler_name)
                            handler(resp['params'])
                        if 'id' in resp:
                            self.request_seq = resp['id']
                elif 'result' in resp:
                    if resp['result'] is not None:
                        req_id = resp['id']
                        if req_id in self.req_status:
                            req_type = self.req_status[req_id]
                            if req_type in self.handler_registry:
                                handler_name = self.handler_registry[req_type]
                                handler = getattr(self, handler_name)
                                handler(resp['result'], req_id)
                                self.req_status.pop(req_id)
                                if req_id in self.req_reply:
                                    self.req_reply.pop(req_id)
            except zmq.ZMQError as e:
                self.notifier.setEnabled(True)
                return

    def perform_request(self, method, params):
        if method in self.sender_registry:
            handler_name = self.sender_registry[method]
            handler = getattr(self, handler_name)
            _id = handler(params)
            if 'response_sig' in params:
                if params['requires_response']:
                    self.req_reply[_id] = params['response_sig']
            return _id

    # ------ Spyder plugin registration --------------------------------
    def register_plugin_type(self, plugin_type, notification_sig):
        if plugin_type not in self.plugin_registry:
            self.plugin_registry[plugin_type] = []
        self.plugin_registry[plugin_type].append(notification_sig)

    # ------ LSP initialization methods --------------------------------
    @handles(SERVER_READY)
    @send_request(method=LSPRequestTypes.INITIALIZE)
    def initialize(self, *args, **kwargs):
        params = {
            'processId': self.transport_client.pid,
            'rootUri': pathlib.Path(osp.abspath(self.folder)).as_uri(),
            'initializationOptions': {
                'pylsPlugins': {
                    'pydocstyle': {'enabled': True},
                    'rope_completion': {'enabled': True}
                }
            },
            'capabilities': self.client_capabilites,
            'trace': TRACE
        }
        return params

    @send_request(method=LSPRequestTypes.SHUTDOWN)
    def shutdown(self):
        params = {}
        return params

    @handles(LSPRequestTypes.SHUTDOWN)
    def handle_shutdown(self, response, *args):
        self.ready_to_close = True

    @send_request(method=LSPRequestTypes.EXIT, requires_response=False)
    def exit(self):
        params = {}
        return params

    @handles(LSPRequestTypes.INITIALIZE)
    def process_server_capabilities(self, server_capabilites, *args):
        self.initialized = True
        server_capabilites = server_capabilites['capabilities']

        if isinstance(server_capabilites['textDocumentSync'], int):
            kind = server_capabilites['textDocumentSync']
            server_capabilites['textDocumentSync'] = TEXT_DOCUMENT_SYNC_OPTIONS
            server_capabilites['textDocumentSync']['change'] = kind

        self.server_capabilites.update(server_capabilites)

        for sig in self.plugin_registry[LSPEventTypes.DOCUMENT]:
            sig.emit(self.server_capabilites, self.language)


def test():
    """Test LSP client."""
    from spyder.utils.qthelpers import qapplication
    app = qapplication(test_time=8)
    server_args_fmt = '--host %(host)s --port %(port)s --tcp'
    server_settings = {'host': '127.0.0.1', 'port': 2087, 'cmd': 'pyls'}
    lsp = LSPClient(app, server_args_fmt, server_settings)
    lsp.start()

    app.aboutToQuit.connect(lsp.stop)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    sys.exit(app.exec_())


if __name__ == "__main__":
    test()

# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder Language Server Protocol Client implementation.

This client implements the calls and procedures required to
communicate with a v3.0 Language Server Protocol server.
"""

# Standard library imports
import logging
import os
import os.path as osp
import signal
import subprocess
import sys

# Third-party imports
from qtpy.QtCore import QObject, Signal, QSocketNotifier, Slot
import zmq

# Local imports
from spyder.py3compat import PY2
from spyder.config.base import get_conf_path, get_debug_level
from spyder.plugins.editor.lsp import (
    CLIENT_CAPABILITES, SERVER_CAPABILITES, TRACE,
    TEXT_DOCUMENT_SYNC_OPTIONS, LSPRequestTypes,
    ClientConstants)
from spyder.plugins.editor.lsp.decorators import (
    send_request, class_register, handles)
from spyder.plugins.editor.lsp.providers import LSPMethodProviderMixIn
from spyder.utils.misc import getcwd_or_home

# Conditional imports
if PY2:
    import pathlib2 as pathlib
else:
    import pathlib

# Main constants
LOCATION = osp.realpath(osp.join(os.getcwd(),
                                 osp.dirname(__file__)))
PENDING = 'pending'
SERVER_READY = 'server_ready'


logger = logging.getLogger(__name__)


@class_register
class LSPClient(QObject, LSPMethodProviderMixIn):
    """Language Server Protocol v3.0 client implementation."""
    #: Signal to inform the editor plugin that the client has
    #  started properly and it's ready to be used.
    sig_initialize = Signal(dict, str)

    #: Signal to report internal server errors through Spyder's
    #  facilities.
    sig_server_error = Signal(str)

    # Constants
    external_server_fmt = ('--server-host %(host)s '
                           '--server-port %(port)s ')

    def __init__(self, parent,
                 server_settings={},
                 folder=getcwd_or_home(),
                 language='python'):
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
        self.watched_files = {}
        self.req_reply = {}

        self.transport_args = [sys.executable, '-u',
                               osp.join(LOCATION, 'transport', 'main.py')]
        self.external_server = server_settings.get('external', False)
        self.stdio = server_settings.get('stdio', False)
        # Setting stdio on implies that external_server is off
        if self.stdio and self.external_server:
            error = ('If server is set to use stdio communication, '
                     'then it cannot be an external server')
            logger.error(error)
            raise AssertionError(error)

        self.folder = folder
        self.plugin_configurations = server_settings.get('configurations', {})
        self.client_capabilites = CLIENT_CAPABILITES
        self.server_capabilites = SERVER_CAPABILITES
        self.context = zmq.Context()

        server_args_fmt = server_settings.get('args', '')
        server_args = server_args_fmt.format(**server_settings)
        transport_args = self.external_server_fmt % (server_settings)

        self.server_args = []
        if language == 'python':
            self.server_args += [sys.executable, '-m']
        self.server_args += [server_settings['cmd']]
        if len(server_args) > 0:
            self.server_args += server_args.split(' ')

        self.transport_args += transport_args.split(' ')
        self.transport_args += ['--folder', folder]
        self.transport_args += ['--transport-debug', str(get_debug_level())]
        if not self.stdio:
            self.transport_args += ['--external-server']
        else:
            self.transport_args += ['--stdio-server']
            self.external_server = True

    def start(self):
        self.zmq_out_socket = self.context.socket(zmq.PAIR)
        self.zmq_out_port = self.zmq_out_socket.bind_to_random_port('tcp://*')
        self.zmq_in_socket = self.context.socket(zmq.PAIR)
        self.zmq_in_socket.set_hwm(0)
        self.zmq_in_port = self.zmq_in_socket.bind_to_random_port('tcp://*')
        self.transport_args += ['--zmq-in-port', self.zmq_out_port,
                                '--zmq-out-port', self.zmq_in_port]

        server_log = subprocess.PIPE
        if get_debug_level() > 0:
            # Create server log file
            server_log_fname = 'server_{0}.log'.format(self.language)
            server_log_file = get_conf_path(osp.join('lsp_logs',
                                                     server_log_fname))
            if not osp.exists(osp.dirname(server_log_file)):
                os.makedirs(osp.dirname(server_log_file))
            server_log = open(server_log_file, 'w')
            if self.stdio:
                server_log.close()
                if self.language == 'python':
                    self.server_args += ['--log-file', server_log_file]
                self.transport_args += ['--server-log-file', server_log_file]

            # Start server with logging options
            if get_debug_level() == 2:
                self.server_args.append('-v')
            elif get_debug_level() == 3:
                self.server_args.append('-vv')

        server_stdin = subprocess.PIPE
        server_stdout = server_log
        server_stderr = subprocess.STDOUT

        if not self.external_server:
            logger.info('Starting server: {0}'.format(
                ' '.join(self.server_args)))
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = (subprocess.CREATE_NEW_PROCESS_GROUP
                                  | 0x08000000)  # CREATE_NO_WINDOW

            if os.environ.get('CI') and os.name == 'nt':
                # The following patching avoids:
                #
                # OSError: [WinError 6] The handle is invalid
                #
                # while running our tests in CI services on Windows
                # (they run fine locally).
                # See this comment for an explanation:
                # https://stackoverflow.com/q/43966523/
                # 438386#comment74964124_43966523
                def patched_cleanup():
                    pass
                subprocess._cleanup = patched_cleanup

            self.lsp_server = subprocess.Popen(
                self.server_args,
                stdout=server_stdout,
                stdin=server_stdin,
                stderr=server_stderr,
                creationflags=creation_flags)

        client_log = subprocess.PIPE
        if get_debug_level() > 0:
            # Client log file
            client_log_fname = 'client_{0}.log'.format(self.language)
            client_log_file = get_conf_path(osp.join('lsp_logs',
                                                     client_log_fname))
            if not osp.exists(osp.dirname(client_log_file)):
                os.makedirs(osp.dirname(client_log_file))
            client_log = open(client_log_file, 'w')

        new_env = dict(os.environ)
        python_path = os.pathsep.join(sys.path)[1:]
        new_env['PYTHONPATH'] = python_path
        self.transport_args = list(map(str, self.transport_args))
        logger.info('Starting transport: {0}'
                    .format(' '.join(self.transport_args)))
        if self.stdio:
            transport_stdin = subprocess.PIPE
            transport_stdout = subprocess.PIPE
            transport_stderr = client_log
            self.transport_args += self.server_args
        else:
            transport_stdout = client_log
            transport_stdin = subprocess.PIPE
            transport_stderr = subprocess.STDOUT
        self.transport_client = subprocess.Popen(self.transport_args,
                                                 stdout=transport_stdout,
                                                 stdin=transport_stdin,
                                                 stderr=transport_stderr,
                                                 env=new_env)

        fid = self.zmq_in_socket.getsockopt(zmq.FD)
        self.notifier = QSocketNotifier(fid, QSocketNotifier.Read, self)
        self.notifier.activated.connect(self.on_msg_received)

        # This is necessary for tests to pass locally!
        logger.debug('LSP {} client started!'.format(self.language))

    def stop(self):
        # self.shutdown()
        # self.exit()
        logger.info('Stopping {} client...'.format(self.language))
        if self.notifier is not None:
            self.notifier.activated.disconnect(self.on_msg_received)
            self.notifier.setEnabled(False)
            self.notifier = None
        # if os.name == 'nt':
        #     self.transport_client.send_signal(signal.CTRL_BREAK_EVENT)
        # else:
        self.transport_client.kill()
        self.context.destroy()
        if not self.external_server:
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

        logger.debug('{} request: {}'.format(self.language, method))
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

                try:
                    method = resp['method']
                    logger.debug(
                        '{} response: {}'.format(self.language, method))
                except KeyError:
                    pass

                if 'error' in resp:
                    logger.debug('{} Response error: {}'
                                 .format(self.language, repr(resp['error'])))
                    if self.language == 'python':
                        traceback = (resp['error'].get('data', {}).
                                     get('traceback'))
                        if traceback:
                            traceback = ''.join(traceback)
                            self.sig_server_error.emit(traceback)
                elif 'method' in resp:
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
            except zmq.ZMQError:
                self.notifier.setEnabled(True)
                return

    def perform_request(self, method, params):
        if method in self.sender_registry:
            handler_name = self.sender_registry[method]
            handler = getattr(self, handler_name)
            _id = handler(params)
            if 'response_codeeditor' in params:
                if params['requires_response']:
                    self.req_reply[_id] = params['response_codeeditor']
            return _id

    # ------ LSP initialization methods --------------------------------
    @handles(SERVER_READY)
    @send_request(method=LSPRequestTypes.INITIALIZE)
    def initialize(self, *args, **kwargs):
        params = {
            'processId': self.transport_client.pid,
            'rootUri': pathlib.Path(osp.abspath(self.folder)).as_uri(),
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
        self.send_plugin_configurations(self.plugin_configurations)
        self.initialized = True
        server_capabilites = server_capabilites['capabilities']

        if isinstance(server_capabilites['textDocumentSync'], int):
            kind = server_capabilites['textDocumentSync']
            server_capabilites['textDocumentSync'] = TEXT_DOCUMENT_SYNC_OPTIONS
            server_capabilites['textDocumentSync']['change'] = kind
        if server_capabilites['textDocumentSync'] is None:
            server_capabilites.pop('textDocumentSync')

        self.server_capabilites.update(server_capabilites)

        self.sig_initialize.emit(self.server_capabilites, self.language)

    @send_request(method=LSPRequestTypes.WORKSPACE_CONFIGURATION_CHANGE,
                  requires_response=False)
    def send_plugin_configurations(self, configurations, *args):
        self.plugin_configurations = configurations
        params = {
            'settings': configurations
        }
        return params


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

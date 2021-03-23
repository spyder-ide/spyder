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
import sys
import time

# Third-party imports
from qtpy.QtCore import (QObject, QProcess, QProcessEnvironment,
                         QSocketNotifier, Signal, Slot)
import zmq
import psutil

# Local imports
from spyder.config.base import (DEV, get_conf_path, get_debug_level,
                                running_under_pytest)
from spyder.plugins.completion.api import (
    CLIENT_CAPABILITES, SERVER_CAPABILITES,
    TEXT_DOCUMENT_SYNC_OPTIONS, CompletionRequestTypes,
    ClientConstants)
from spyder.plugins.completion.providers.languageserver.decorators import (
    send_request, send_notification, class_register, handles)
from spyder.plugins.completion.providers.languageserver.transport import (
    MessageKind)
from spyder.plugins.completion.providers.languageserver.providers import (
    LSPMethodProviderMixIn)
from spyder.py3compat import PY2
from spyder.utils.misc import getcwd_or_home, select_port

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
LOCALHOST = '127.0.0.1'

# Language server communication verbosity at server logs.
TRACE = 'messages'
if DEV:
    TRACE = 'verbose'

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

    #: Signal to warn the user when either the transport layer or the
    #  server went down
    sig_went_down = Signal(str)

    def __init__(self, parent,
                 server_settings={},
                 folder=getcwd_or_home(),
                 language='python'):
        QObject.__init__(self)
        self.manager = parent
        self.zmq_in_socket = None
        self.zmq_out_socket = None
        self.zmq_in_port = None
        self.zmq_out_port = None
        self.transport = None
        self.server = None
        self.stdio_pid = None
        self.notifier = None
        self.language = language

        self.initialized = False
        self.ready_to_close = False
        self.request_seq = 1
        self.req_status = {}
        self.watched_files = {}
        self.watched_folders = {}
        self.req_reply = {}
        self.server_unresponsive = False
        self.transport_unresponsive = False

        # Select a free port to start the server.
        # NOTE: Don't use the new value to set server_setttings['port']!!
        # That's not required because this doesn't really correspond to a
        # change in the config settings of the server. Else a server
        # restart would be generated when doing a
        # workspace/didChangeConfiguration request.
        if not server_settings['external']:
            self.server_port = select_port(
                default_port=server_settings['port'])
        else:
            self.server_port = server_settings['port']
        self.server_host = server_settings['host']

        self.external_server = server_settings.get('external', False)
        self.stdio = server_settings.get('stdio', False)

        # Setting stdio on implies that external_server is off
        if self.stdio and self.external_server:
            error = ('If server is set to use stdio communication, '
                     'then it cannot be an external server')
            logger.error(error)
            raise AssertionError(error)

        self.folder = folder
        self.configurations = server_settings.get('configurations', {})
        self.client_capabilites = CLIENT_CAPABILITES
        self.server_capabilites = SERVER_CAPABILITES
        self.context = zmq.Context()

        # To set server args
        self._server_args = server_settings.get('args', '')
        self._server_cmd = server_settings['cmd']

        # Save requests name and id. This is only necessary for testing.
        self._requests = []

    def _get_log_filename(self, kind):
        """
        Get filename to redirect server or transport logs to in
        debugging mode.

        Parameters
        ----------
        kind: str
            It can be "server" or "transport".
        """
        if get_debug_level() == 0:
            return None

        fname = '{0}_{1}_{2}.log'.format(kind, self.language, os.getpid())
        location = get_conf_path(osp.join('lsp_logs', fname))

        # Create directory that contains the file, in case it doesn't
        # exist
        if not osp.exists(osp.dirname(location)):
            os.makedirs(osp.dirname(location))

        return location

    @property
    def server_log_file(self):
        """
        Filename to redirect the server process stdout/stderr output.
        """
        return self._get_log_filename('server')

    @property
    def transport_log_file(self):
        """
        Filename to redirect the transport process stdout/stderr
        output.
        """
        return self._get_log_filename('transport')

    @property
    def server_args(self):
        """Arguments for the server process."""
        args = []
        if self.language == 'python':
            args += [sys.executable, '-m']
        args += [self._server_cmd]

        # Replace host and port placeholders
        host_and_port = self._server_args.format(
            host=self.server_host,
            port=self.server_port)
        if len(host_and_port) > 0:
            args += host_and_port.split(' ')

        if self.language == 'python' and get_debug_level() > 0:
            args += ['--log-file', self.server_log_file]
            if get_debug_level() == 2:
                args.append('-v')
            elif get_debug_level() == 3:
                args.append('-vv')

        return args

    @property
    def transport_args(self):
        """Arguments for the transport process."""
        args = [
            sys.executable,
            '-u',
            osp.join(LOCATION, 'transport', 'main.py'),
            '--folder', self.folder,
            '--transport-debug', str(get_debug_level())
        ]

        # Replace host and port placeholders
        host_and_port = '--server-host {host} --server-port {port} '.format(
            host=self.server_host,
            port=self.server_port)
        args += host_and_port.split(' ')

        # Add socket ports
        args += ['--zmq-in-port', str(self.zmq_out_port),
                 '--zmq-out-port', str(self.zmq_in_port)]

        # Adjustments for stdio/tcp
        if self.stdio:
            args += ['--stdio-server']
            if get_debug_level() > 0:
                args += ['--server-log-file', self.server_log_file]
            args += self.server_args
        else:
            args += ['--external-server']

        return args

    def create_transport_sockets(self):
        """Create PyZMQ sockets for transport."""
        self.zmq_out_socket = self.context.socket(zmq.PAIR)
        self.zmq_out_port = self.zmq_out_socket.bind_to_random_port(
            'tcp://{}'.format(LOCALHOST))
        self.zmq_in_socket = self.context.socket(zmq.PAIR)
        self.zmq_in_socket.set_hwm(0)
        self.zmq_in_port = self.zmq_in_socket.bind_to_random_port(
            'tcp://{}'.format(LOCALHOST))

    @Slot(QProcess.ProcessError)
    def handle_process_errors(self, error):
        """Handle errors with the transport layer or server processes."""
        self.sig_went_down.emit(self.language)

    def start_server(self):
        """Start server."""
        # This is not necessary if we're trying to connect to an
        # external server
        if self.external_server or self.stdio:
            return

        logger.info('Starting server: {0}'.format(' '.join(self.server_args)))

        # Create server process
        self.server = QProcess(self)
        env = self.server.processEnvironment()

        # Use local PyLS instead of site-packages one.
        if DEV or running_under_pytest():
            running_in_ci = bool(os.environ.get('CI'))
            if os.name != 'nt' or os.name == 'nt' and not running_in_ci:
                env.insert('PYTHONPATH', os.pathsep.join(sys.path)[:])

        # Adjustments for the Python language server.
        if self.language == 'python':
            # Set the PyLS current working to an empty dir inside
            # our config one. This avoids the server to pick up user
            # files such as random.py or string.py instead of the
            # standard library modules named the same.
            cwd = osp.join(get_conf_path(), 'lsp_paths', 'cwd')
            if not osp.exists(cwd):
                os.makedirs(cwd)

            # On Windows, some modules (notably Matplotlib)
            # cause exceptions if they cannot get the user home.
            # So, we need to pass the USERPROFILE env variable to
            # the PyLS.
            if os.name == "nt" and "USERPROFILE" in os.environ:
                env.insert("USERPROFILE", os.environ["USERPROFILE"])
        else:
            # There's no need to define a cwd for other servers.
            cwd = None

            # Most LSP servers spawn other processes, which may require
            # some environment variables.
            for var in os.environ:
                env.insert(var, os.environ[var])
            logger.info('Server process env variables: {0}'.format(env.keys()))

        # Setup server
        self.server.setProcessEnvironment(env)
        self.server.errorOccurred.connect(self.handle_process_errors)
        self.server.setWorkingDirectory(cwd)
        self.server.setProcessChannelMode(QProcess.MergedChannels)
        if self.server_log_file is not None:
            self.server.setStandardOutputFile(self.server_log_file)

        # Start server
        self.server.start(self.server_args[0], self.server_args[1:])

    def start_transport(self):
        """Start transport layer."""
        logger.info('Starting transport for {1}: {0}'
                    .format(' '.join(self.transport_args), self.language))

        # Create transport process
        self.transport = QProcess(self)
        env = self.transport.processEnvironment()

        # Most LSP servers spawn other processes other than Python, which may
        # require some environment variables
        if self.language != 'python' and self.stdio:
            for var in os.environ:
                env.insert(var, os.environ[var])
            logger.info('Transport process env variables: {0}'.format(
                env.keys()))

        self.transport.setProcessEnvironment(env)

        # Modifying PYTHONPATH to run transport in development mode or
        # tests
        if DEV or running_under_pytest():
            if running_under_pytest():
                env.insert('PYTHONPATH', os.pathsep.join(sys.path)[:])
            else:
                env.insert('PYTHONPATH', os.pathsep.join(sys.path)[1:])
            self.transport.setProcessEnvironment(env)

        # Set up transport
        self.transport.errorOccurred.connect(self.handle_process_errors)
        if self.stdio:
            self.transport.setProcessChannelMode(QProcess.SeparateChannels)
            if self.transport_log_file is not None:
                self.transport.setStandardErrorFile(self.transport_log_file)
        else:
            self.transport.setProcessChannelMode(QProcess.MergedChannels)
            if self.transport_log_file is not None:
                self.transport.setStandardOutputFile(self.transport_log_file)

        # Start transport
        self.transport.start(self.transport_args[0], self.transport_args[1:])

    def start(self):
        """Start client."""
        # NOTE: DO NOT change the order in which these methods are called.
        self.create_transport_sockets()
        self.start_server()
        self.start_transport()

        # Create notifier
        fid = self.zmq_in_socket.getsockopt(zmq.FD)
        self.notifier = QSocketNotifier(fid, QSocketNotifier.Read, self)
        self.notifier.activated.connect(self.on_msg_received)

        # This is necessary for tests to pass locally!
        logger.debug('LSP {} client started!'.format(self.language))

    def stop(self):
        """Stop transport and server."""
        logger.info('Stopping {} client...'.format(self.language))
        if self.notifier is not None:
            self.notifier.activated.disconnect(self.on_msg_received)
            self.notifier.setEnabled(False)
            self.notifier = None
        if self.transport is not None:
            self.transport.kill()
        self.context.destroy()
        if self.server is not None:
            self.server.kill()

    def is_transport_alive(self):
        """Detect if transport layer is alive."""
        state = self.transport.state()
        return state != QProcess.NotRunning

    def is_stdio_alive(self):
        """Check if an stdio server is alive."""
        alive = True
        if not psutil.pid_exists(self.stdio_pid):
            alive = False
        else:
            try:
                pid_status = psutil.Process(self.stdio_pid).status()
            except psutil.NoSuchProcess:
                pid_status = ''
            if pid_status == psutil.STATUS_ZOMBIE:
                alive = False
        return alive

    def is_server_alive(self):
        """Detect if a tcp server is alive."""
        state = self.server.state()
        return state != QProcess.NotRunning

    def is_down(self):
        """
        Detect if the transport layer or server are down to inform our
        users about it.
        """
        is_down = False
        if self.transport and not self.is_transport_alive():
            logger.debug(
                "Transport layer for {} is down!!".format(self.language))
            if not self.transport_unresponsive:
                self.transport_unresponsive = True
                self.sig_went_down.emit(self.language)
            is_down = True

        if self.server and not self.is_server_alive():
            logger.debug("LSP server for {} is down!!".format(self.language))
            if not self.server_unresponsive:
                self.server_unresponsive = True
                self.sig_went_down.emit(self.language)
            is_down = True

        if self.stdio_pid and not self.is_stdio_alive():
            logger.debug("LSP server for {} is down!!".format(self.language))
            if not self.server_unresponsive:
                self.server_unresponsive = True
                self.sig_went_down.emit(self.language)
            is_down = True

        return is_down

    def send(self, method, params, kind):
        """Send message to transport."""
        if self.is_down():
            return

        if ClientConstants.CANCEL in params:
            return
        _id = self.request_seq
        if kind == MessageKind.REQUEST:
            msg = {
                'id': self.request_seq,
                'method': method,
                'params': params
            }
            self.req_status[self.request_seq] = method
        elif kind == MessageKind.RESPONSE:
            msg = {
                'id': self.request_seq,
                'result': params
            }
        elif kind == MessageKind.NOTIFICATION:
            msg = {
                'method': method,
                'params': params
            }

        logger.debug('Perform request {0} with id {1}'.format(method, _id))

        # Save requests to check their ordering.
        if running_under_pytest():
            self._requests.append((_id, method))

        # Try sending a message. If the send queue is full, keep trying for a
        # a second before giving up.
        timeout = 1
        start_time = time.time()
        timeout_time = start_time + timeout
        while True:
            try:
                self.zmq_out_socket.send_pyobj(msg, flags=zmq.NOBLOCK)
                self.request_seq += 1
                return int(_id)
            except zmq.error.Again:
                if time.time() > timeout_time:
                    self.sig_went_down.emit(self.language)
                    return
                # The send queue is full! wait 0.1 seconds before retrying.
                if self.initialized:
                    logger.warning("The send queue is full! Retrying...")
                time.sleep(.1)

    @Slot()
    def on_msg_received(self):
        """Process received messages."""
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
                        # Show PyLS errors in our error report dialog only in
                        # debug or development modes
                        if get_debug_level() > 0 or DEV:
                            message = resp['error'].get('message', '')
                            traceback = (resp['error'].get('data', {}).
                                         get('traceback'))
                            if traceback is not None:
                                traceback = ''.join(traceback)
                                traceback = traceback + '\n' + message
                                self.sig_server_error.emit(traceback)
                        req_id = resp['id']
                        if req_id in self.req_reply:
                            self.req_reply[req_id](None, {'params': []})
                elif 'method' in resp:
                    if resp['method'][0] != '$':
                        if 'id' in resp:
                            self.request_seq = int(resp['id'])
                        if resp['method'] in self.handler_registry:
                            handler_name = (
                                self.handler_registry[resp['method']])
                            handler = getattr(self, handler_name)
                            handler(resp['params'])
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
            except RuntimeError:
                # This is triggered when a codeeditor instance has been
                # removed before the response can be processed.
                pass
            except zmq.ZMQError:
                self.notifier.setEnabled(True)
                return

    def perform_request(self, method, params):
        if method in self.sender_registry:
            handler_name = self.sender_registry[method]
            handler = getattr(self, handler_name)
            _id = handler(params)
            if 'response_callback' in params:
                if params['requires_response']:
                    self.req_reply[_id] = params['response_callback']
            return _id

    # ------ LSP initialization methods --------------------------------
    @handles(SERVER_READY)
    @send_request(method=CompletionRequestTypes.INITIALIZE)
    def initialize(self, params, *args, **kwargs):
        self.stdio_pid = params['pid']
        pid = self.transport.processId() if not self.external_server else None
        params = {
            'processId': pid,
            'rootUri': pathlib.Path(osp.abspath(self.folder)).as_uri(),
            'capabilities': self.client_capabilites,
            'trace': TRACE
        }
        return params

    @send_request(method=CompletionRequestTypes.SHUTDOWN)
    def shutdown(self):
        params = {}
        return params

    @handles(CompletionRequestTypes.SHUTDOWN)
    def handle_shutdown(self, response, *args):
        self.ready_to_close = True

    @send_notification(method=CompletionRequestTypes.EXIT)
    def exit(self):
        params = {}
        return params

    @handles(CompletionRequestTypes.INITIALIZE)
    def process_server_capabilities(self, server_capabilites, *args):
        """
        Register server capabilities and inform other plugins that it's
        available.
        """
        # Update server capabilities with the info sent by the server.
        server_capabilites = server_capabilites['capabilities']

        if isinstance(server_capabilites['textDocumentSync'], int):
            kind = server_capabilites['textDocumentSync']
            server_capabilites['textDocumentSync'] = TEXT_DOCUMENT_SYNC_OPTIONS
            server_capabilites['textDocumentSync']['change'] = kind
        if server_capabilites['textDocumentSync'] is None:
            server_capabilites.pop('textDocumentSync')

        self.server_capabilites.update(server_capabilites)

        # The initialized notification needs to be the first request sent by
        # the client according to the protocol.
        self.initialized = True
        self.initialized_call()

        # This sends a DidChangeConfiguration request to pass to the server
        # the configurations set by the user in our config system.
        self.send_configurations(self.configurations)

        # Inform other plugins that the server is up.
        self.sig_initialize.emit(self.server_capabilites, self.language)

    @send_notification(method=CompletionRequestTypes.INITIALIZED)
    def initialized_call(self):
        params = {}
        return params

    # ------ Settings queries --------------------------------
    @property
    def support_multiple_workspaces(self):
        workspace_settings = self.server_capabilites['workspace']
        return workspace_settings['workspaceFolders']['supported']

    @property
    def support_workspace_update(self):
        workspace_settings = self.server_capabilites['workspace']
        return workspace_settings['workspaceFolders']['changeNotifications']


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

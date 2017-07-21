# -*- coding: utf-8 -*-

"""Spyder MS Language Server v3.0 client implementation."""

import os
import zmq
import json
import time
import psutil
import signal
import socket
import logging
import argparse
import subprocess
import coloredlogs
import os.path as osp
from threading import Thread, Lock
from spyder.py3compat import PY2, getcwd
from spyder.utils.code_analysis import EDITOR_CAPABILITES, TRACE

if PY2:
    import pathlib2 as pathlib
else:
    import pathlib


TIMEOUT = 5000
PID = os.getpid()


parser = argparse.ArgumentParser(
    description='ZMQ Python-based MS Language-Server v3.0 client for Spyder')

parser.add_argument('--zmq-port',
                    default=7000,
                    help="ZMQ port to be contacted")
parser.add_argument('--server-host',
                    default='127.0.0.1',
                    help='Host that serves the ls-server')
parser.add_argument('--server-port',
                    default=2087,
                    help="Deployment port of the ls-server")
parser.add_argument('--folder',
                    default=getcwd(),
                    help="Initial current working directory used to "
                         "initialize ls-server")
parser.add_argument('--server',
                    default='pyls',
                    help='Instruction executed to start the language server')
parser.add_argument('--external-server',
                    action="store_true",
                    help="Do not start a local server")
parser.add_argument('--debug',
                    action='store_true',
                    help='Display debug level log messages')

args, unknownargs = parser.parse_known_args()

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')

# LOG_FORMAT = ('%(asctime)s %(hostname)s %(name)s[%(process)d] '
#               '(%(funcName)s: %(lineno)d) %(levelname)s %(message)s')

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
logging.basicConfig(level=logging.ERROR, format=LOG_FORMAT)

LOGGER = logging.getLogger(__name__)

LEVEL = 'info'
if args.debug:
    LEVEL = 'debug'

coloredlogs.install(level=LEVEL)


class IncomingMessageThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.stopped = False
        self.mutex = Lock()

    def initialize(self, sock, zmq_sock):
        self.socket = sock
        self.zmq_sock = zmq_sock

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


class LanguageServerClient:
    """Implementation of a v3.0 compilant language server client."""
    CONTENT_LENGTH = 'Content-Length: {0}\r\n\r\n'

    def __init__(self, host='127.0.0.1', port=2087, workspace=getcwd(),
                 use_external_server=False, zmq_port=7000,
                 server='pyls', server_args=['--tcp']):
        self.host = host
        self.port = port
        self.workspace = pathlib.Path(osp.abspath(workspace)).as_uri()
        self.request_seq = 1

        self.server = None
        self.is_local_server_running = not use_external_server
        if not use_external_server:
            LOGGER.info('Starting server: {0} {1} on {2}:{3}'.format(
                server, ' '.join(server_args), self.host, self.port))
            exec_line = [server, '--host', str(self.host), '--port',
                         str(self.port)] + server_args
            LOGGER.info(' '.join(exec_line))

            self.server = subprocess.Popen(
                exec_line,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)

            LOGGER.info('Waiting server to start...')
            time.sleep(3)

        LOGGER.info('Connecting to language server at {0}:{1}'.format(
            self.host, self.port))
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, int(self.port)))
        self.socket.setblocking(False)

        LOGGER.info('Initializing server connection...')
        self.__initialize()

        LOGGER.info('Starting ZMQ connection...')
        self.context = zmq.Context()
        self.zmq_socket = self.context.socket(zmq.PAIR)
        self.zmq_socket.connect("tcp://localhost:{0}".format(zmq_port))
        self.zmq_socket.send_pyobj(zmq_port)

        LOGGER.info('Creating consumer Thread...')
        self.reading_thread = IncomingMessageThread()
        self.reading_thread.initialize(self.socket, self.zmq_socket)

    def __initialize(self):
        method = 'initialize'
        params = {
            'processId': PID,
            'rootUri': self.workspace,
            'capabilities': EDITOR_CAPABILITES,
            'trace': TRACE
        }
        request = self.__compose_request(method, params)
        self.__send_request(request)

    def start(self):
        LOGGER.info('Ready to recieve/attend requests and responses!')
        self.reading_thread.start()

    def stop(self):
        LOGGER.info('Sending shutdown instruction to server')
        self.shutdown()
        LOGGER.info('Stopping language server')
        self.exit()
        LOGGER.info('Closing TCP socket...')
        self.socket.close()
        if self.is_local_server_running:
            LOGGER.info('Closing language server process...')
            self.server.terminate()
        LOGGER.info('Closing consumer thread...')
        self.reading_thread.stop()
        LOGGER.debug('Joining thread...')
        self.reading_thread.join()
        LOGGER.debug('Exit routine should be complete')

    def shutdown(self):
        method = 'shutdown'
        params = {}
        request = self.__compose_request(method, params)
        self.__send_request(request)

    def exit(self):
        method = 'exit'
        params = {}
        request = self.__compose_request(method, params)
        self.__send_request(request)

    def listen(self):
        events = self.zmq_socket.poll(TIMEOUT)
        requests = []
        while events > 0:
            client_request = self.zmq_socket.recv_pyobj()
            LOGGER.debug("Client Event: {0}".format(client_request))
            requests.append(client_request)
            server_request = self.__compose_request('None', {})
            self.__send_request(server_request)

    def __compose_request(self, method, params):
        request = {
            "jsonrpc": "2.0",
            "id": self.request_seq,
            "method": method,
            "params": params
        }
        return request

    def __send_request(self, request):
        json_req = json.dumps(request)
        content = bytes(json_req.encode('utf-8'))
        content_length = len(content)

        LOGGER.debug('Sending request of type: {0}'.format(request['method']))
        LOGGER.debug(json_req)

        content_length = self.CONTENT_LENGTH.format(
            content_length).encode('utf-8')
        self.socket.send(bytes(content_length))
        self.socket.send(content)
        self.request_seq += 1


class TerminateSignal(Exception):
    """Terminal exception descriptor."""
    pass


class SignalManager:
    """Manage and intercept SIGTERM and SIGKILL signals."""

    def __init__(self):
        self.original_sigint = signal.getsignal(signal.SIGINT)
        self.original_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        LOGGER.info('Termination signal ({}) captured, '
                    'initiating exit sequence'.format(signum))
        raise TerminateSignal("Exit process!")

    def restore(self):
        signal.signal(signal.SIGINT, self.original_sigint)
        signal.signal(signal.SIGTERM, self.original_sigterm)


if __name__ == '__main__':
    process = psutil.Process()
    sig_manager = SignalManager()
    client = LanguageServerClient(host=args.server_host,
                                  port=args.server_port,
                                  workspace=args.folder,
                                  zmq_port=args.zmq_port,
                                  use_external_server=args.external_server,
                                  server=args.server,
                                  server_args=unknownargs)
    client.start()
    try:
        while True:
            client.listen()
    except TerminateSignal:
        pass
    client.stop()
    sig_manager.restore()
    process.terminate()
    process.wait()

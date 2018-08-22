# -*- coding: utf-8 -*-

"""
Spyder MS Language Server v3.0 transport proxy implementation.

Main point-of-entry to start an LSP ZMQ/TCP transport proxy.
"""

import os
import psutil
import signal
import logging
import argparse
import coloredlogs
from spyder.py3compat import getcwd
from producer import LanguageServerClient


WINDOWS = os.name == 'nt'


parser = argparse.ArgumentParser(
    description='ZMQ Python-based MS Language-Server v3.0 client for Spyder')

parser.add_argument('--zmq-in-port',
                    default=7000,
                    help="ZMQ (in) port to be contacted")
parser.add_argument('--zmq-out-port',
                    default=7001,
                    help="ZMQ (out) port to be contacted")
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
parser.add_argument('--transport-debug',
                    action='store_true',
                    help='Display debug level log messages')

args, unknownargs = parser.parse_known_args()

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
logging.basicConfig(level=logging.ERROR, format=LOG_FORMAT)

LOGGER = logging.getLogger(__name__)

LEVEL = 'info'
if args.transport_debug:
    LEVEL = 'debug'

coloredlogs.install(level=LEVEL)


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
        if WINDOWS:
            self.original_sigbreak = signal.getsignal(signal.SIGBREAK)
            signal.signal(signal.SIGBREAK, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        """Capture exit/kill signal and throw and exception."""
        LOGGER.info('Termination signal ({}) captured, '
                    'initiating exit sequence'.format(signum))
        raise TerminateSignal("Exit process!")

    def restore(self):
        """Restore signal handlers to their original settings."""
        signal.signal(signal.SIGINT, self.original_sigint)
        signal.signal(signal.SIGTERM, self.original_sigterm)
        if WINDOWS:
            signal.signal(signal.SIGBREAK, self.original_sigbreak)


if __name__ == '__main__':
    process = psutil.Process()
    sig_manager = SignalManager()
    client = LanguageServerClient(host=args.server_host,
                                  port=args.server_port,
                                  workspace=args.folder,
                                  zmq_in_port=args.zmq_in_port,
                                  zmq_out_port=args.zmq_out_port,
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
    # sig_manager.restore()
    process.terminate()
    process.wait()

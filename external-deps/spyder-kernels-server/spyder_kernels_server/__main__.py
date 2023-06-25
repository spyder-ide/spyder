# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------
import os
import sys
import zmq
import json
import argparse
from spyder_kernels_server.kernel_server import KernelServer
from zmq.ssh import tunnel as zmqtunnel
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QSocketNotifier, QObject, QCoreApplication, Slot


class Server(QObject):
    def __init__(self, main_port=None, pub_port=None):
        super().__init__()

        if main_port is None:
            main_port = str(zmqtunnel.select_random_ports(1)[0])

        context = zmq.Context()
        self.socket = context.socket(zmq.REP)
        self.socket.bind("tcp://*:%s" % main_port)
        print(f"Server running on port {main_port}")
        self.kernel_server = KernelServer()

        self._notifier = QSocketNotifier(
            self.socket.getsockopt(zmq.FD), QSocketNotifier.Read, self
        )
        self._notifier.activated.connect(self._socket_activity)

        self.port_pub = pub_port
        if pub_port is None:
            self.port_pub = str(zmqtunnel.select_random_ports(1)[0])
        self.socket_pub = context.socket(zmq.PUB)
        self.socket_pub.bind("tcp://*:%s" % self.port_pub)

        self.kernel_server.sig_kernel_restarted.connect(
            self._handle_kernel_restarted
        )

    def _socket_activity(self):
        self._notifier.setEnabled(False)
        #  Wait for next request from client
        message = self.socket.recv_pyobj()
        cmd = message[0]
        if cmd == "get_port_pub":
            self.socket.send_pyobj(["set_port_pub", self.port_pub])
        elif cmd == "shutdown":
            self.socket.send_pyobj(["shutting_down"])
            self.kernel_server.shutdown()

        elif cmd == "open_kernel":
            try:
                cf = self.kernel_server.open_kernel(message[1])
                with open(cf, "br") as f:
                    cf = (cf, json.load(f))

            except Exception as e:
                cf = ("error", e)
            self.socket.send_pyobj(["new_kernel", *cf])

        elif cmd == "close_kernel":
            self.socket.send_pyobj(["closing_kernel"])
            try:
                self.kernel_server.close_kernel(message[1])
            except Exception:
                pass
        self._notifier.setEnabled(True)

        # This is necessary for some reason.
        # Otherwise the socket only works twice !
        self.socket.getsockopt(zmq.EVENTS)

    @Slot(str)
    def _handle_kernel_restarted(self, connection_file):
        self.socket_pub.send_pyobj(["kernel_restarted", connection_file])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Spyder Kernels Server",
        description="Server to start and manage spyder kernels",
    )

    parser.add_argument("port", default=None, nargs="?")
    parser.add_argument("port_pub", default=None, nargs="?")
    parser.add_argument("-i", "--interactive", action="store_true")
    args = parser.parse_args()
    if args.interactive:
        app = QApplication(sys.argv)
    else:
        app = QCoreApplication(sys.argv)
    w = Server(args.port, args.port_pub)
    sys.exit(app.exec_())

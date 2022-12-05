# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------
import sys
import zmq
import json
from spyder_kernels_server.kernel_server import KernelServer
from zmq.ssh import tunnel as zmqtunnel
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import QSocketNotifier, QObject, QCoreApplication


class Server(QObject):

    def __init__(self):
        super().__init__()

        if len(sys.argv) > 1:
            port = sys.argv[1]
        else:
            port = str(zmqtunnel.select_random_ports(1)[0])

        context = zmq.Context()
        self.socket = context.socket(zmq.REP)
        self.socket.bind("tcp://*:%s" % port)
        print(f"Server running on port {port}")
        self.kernel_server = KernelServer()

        self._notifier = QSocketNotifier(self.socket.getsockopt(zmq.FD),
                                         QSocketNotifier.Read, self)
        self._notifier.activated.connect(self._socket_activity)

    def _socket_activity(self):
        self._notifier.setEnabled(False)
        #  Wait for next request from client
        message = self.socket.recv_pyobj()
        print(message)
        cmd = message[0]
        if cmd == "shutdown":
            self.socket.send_pyobj(["shutting_down"])
            self.kernel_server.shutdown()

        elif cmd == "open_kernel":
            try:
                cf = self.kernel_server.open_kernel(message[1])
                print(cf)
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
                print("Nope")
                pass
        self._notifier.setEnabled(True)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Server()
    sys.exit(app.exec_())
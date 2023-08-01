# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
IPython Console mixins.
"""
import zmq
import sys
import os
import queue

from qtpy.QtCore import QProcess, QSocketNotifier, Slot

# Local imports
from spyder.api.config.mixins import SpyderConfigurationObserver
from spyder.plugins.ipythonconsole.utils.kernel_handler import KernelHandler
from spyder.api.config.decorators import on_conf_change
from zmq.ssh import tunnel as zmqtunnel
from spyder.plugins.ipythonconsole.utils.ssh import openssh_tunnel

if os.name == "nt":
    ssh_tunnel = zmqtunnel.paramiko_tunnel
else:
    ssh_tunnel = openssh_tunnel


KERNEL_SERVER_OPTIONS = [
    "kernel_server/external_server",
    "kernel_server/use_ssh",
    "kernel_server/host",
    "kernel_server/port",
    "kernel_server/username",
    "kernel_server/password_auth",
    "kernel_server/keyfile_auth",
    "kernel_server/password",
    "kernel_server/keyfile",
    "kernel_server/passphrase",
]


class KernelConnectorMixin(SpyderConfigurationObserver):
    """Needs https://github.com/jupyter/jupyter_client/pull/835"""

    def __init__(self):
        super().__init__()
        self.options = None
        self.server = None
        self.kernel_handler_waitlist = []
        self._alive_kernel_handlers = {}
        self.request_queue = queue.Queue()
        self.context = zmq.Context()
        self.on_kernel_server_conf_changed()

    @on_conf_change(option=KERNEL_SERVER_OPTIONS, section="main_interpreter")
    def on_kernel_server_conf_changed(self, option=None, value=None):
        """Start server"""
        options = {
            option: self.get_conf(option=option, section="main_interpreter")
            for option in KERNEL_SERVER_OPTIONS
        }
        if self.options == options:
            return

        if self.server is not None:
            self.stop_local_server()

        if self.options is not None:
            # Close cached kernel
            self.close_cached_kernel()
            # Reset request_queue
            self.request_queue = queue.Queue()
            # Send new kernel request for waiting kernels
            for kernel_handler in self.kernel_handler_waitlist:
                self.send_request(
                    ["open_kernel", kernel_handler.kernel_spec_dict]
                )

        self.options = options
        self.ssh_remote_hostname = None
        self.ssh_key = None
        self.ssh_password = None

        is_remote = options["kernel_server/external_server"]

        if not is_remote:
            self.start_local_server()
            return

        # Remote server

        remote_port = int(options["kernel_server/port"])
        if not remote_port:
            remote_port = 22
        remote_ip = options["kernel_server/host"]

        is_ssh = options["kernel_server/use_ssh"]

        if not is_ssh:
            self.connect_socket(remote_ip, remote_port)
            return

        username = options["kernel_server/username"]

        self.ssh_remote_hostname = f"{username}@{remote_ip}:{remote_port}"

        # Now we deal with ssh
        uses_password = options["kernel_server/password_auth"]
        uses_keyfile = options["kernel_server/keyfile_auth"]

        if uses_password:
            self.ssh_password = options["kernel_server/password"]
            self.ssh_key = None
        elif uses_keyfile:
            self.ssh_password = options["kernel_server/passphrase"]
            self.ssh_key = options["kernel_server/keyfile"]
        else:
            raise NotImplementedError("This should not be possible.")

        self.connect_socket(remote_ip, remote_port)

    def start_local_server(self):
        """Start a server with the current interpreter."""
        port = str(zmqtunnel.select_random_ports(1)[0])
        self.server = QProcess(self)
        self.server.start(
            sys.executable, ["-m", "spyder_kernels_server", port]
        )
        self.server.readyReadStandardError.connect(self.print_server_stderr)
        self.server.readyReadStandardOutput.connect(self.print_server_stdout)
        self.connect_socket("localhost", port)

    def stop_local_server(self, wait=False):
        """Stop local server."""
        if self.server is None:
            return
        self.server.readyReadStandardError.disconnect(self.print_server_stderr)
        self.server.readyReadStandardOutput.disconnect(
            self.print_server_stdout
        )
        self.send_request(["shutdown"])
        if wait:
            self.server.waitForFinished()
        self.server = None

    @Slot()
    def print_server_stderr(self):
        sys.stderr.write(self.server.readAllStandardError().data().decode())

    @Slot()
    def print_server_stdout(self):
        sys.stdout.write(self.server.readAllStandardOutput().data().decode())

    def connect_socket(self, hostname, port):
        self.hostname = hostname

        hostname, port = self.tunnel_ssh(hostname, port)

        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{hostname}:{port}")
        self._notifier = QSocketNotifier(
            self.socket.getsockopt(zmq.FD), QSocketNotifier.Read, self
        )
        self._notifier.activated.connect(self._socket_activity)
        self.send_request(["get_port_pub"])

    def tunnel_ssh(self, hostname, port):
        if self.ssh_remote_hostname is None:
            return hostname, port
        remote_hostname = hostname
        remote_port = port
        port = zmqtunnel.select_random_ports(1)
        hostname = "localhost"
        timeout = 10
        ssh_tunnel(
            port,
            remote_port,
            hostname,
            remote_hostname,
            self.ssh_key,
            self.ssh_password,
            timeout,
        )
        return hostname, port

    def new_kernel(self, kernel_spec_dict):
        """Get a new kernel"""
        
        kernel_handler = KernelHandler.new_from_spec(
            kernel_spec_dict=kernel_spec_dict,
            hostname=self.ssh_remote_hostname,
            sshkey=self.ssh_key,
            password=self.ssh_password,
        )

        kernel_handler.sig_remote_close.connect(self.request_close)
        self.kernel_handler_waitlist.append(kernel_handler)

        self.send_request(["open_kernel", kernel_spec_dict])

        return kernel_handler

    def request_close(self, connection_file):
        self.send_request(["close_kernel", connection_file])
        # Remove kernel from active kernels
        self._alive_kernel_handlers.pop(connection_file, None)

    def send_request(self, request):
        # Check socket state
        socket_state = self.socket.getsockopt(zmq.EVENTS)
        if socket_state & zmq.POLLOUT:
            self.socket.send_pyobj(request)
        else:
            self.request_queue.put(request)
        # Checking the socket state interferes with the notifier.
        # If the socket is ready, read.
        if socket_state & zmq.POLLIN:
            self._socket_activity()

    @Slot()
    def _socket_activity(self):
        if not self.socket.getsockopt(zmq.EVENTS) & zmq.POLLIN:
            # Valid, see http://api.zeromq.org/master:zmq-getsockopt
            return
        self._notifier.setEnabled(False)
        #  Wait for next request from client
        message = self.socket.recv_pyobj()
        cmd = message[0]

        if cmd == "new_kernel":
            cmd, connection_file, connection_info = message

            if len(self.kernel_handler_waitlist) == 0:
                # This should not happen :/
                self._notifier.setEnabled(True)
                self.socket.getsockopt(zmq.EVENTS)
                return

            kernel_handler = self.kernel_handler_waitlist.pop(0)
            if connection_file == "error":
                kernel_handler.handle_stderr(str(connection_info))
            else:
                kernel_handler.set_connection(
                    connection_file,
                    connection_info,
                    self.ssh_remote_hostname,
                    self.ssh_key,
                    self.ssh_password,
                )
                # keep ref to signal kernel handler
                self._alive_kernel_handlers[connection_file] = kernel_handler

        elif cmd == "set_port_pub":
            port_pub = message[1]
            self.socket_sub = self.context.socket(zmq.SUB)
            # To recieve everything
            self.socket_sub.setsockopt(zmq.SUBSCRIBE, b"")
            hostname = self.hostname
            hostname, port_pub = self.tunnel_ssh(hostname, port_pub)

            self.socket_sub.connect(f"tcp://{hostname}:{port_pub}")
            self._notifier_sub = QSocketNotifier(
                self.socket_sub.getsockopt(zmq.FD), QSocketNotifier.Read, self
            )
            self._notifier_sub.activated.connect(self._socket_sub_activity)

        self._notifier.setEnabled(True)
        # This is necessary for some reason.
        # Otherwise the notifer is not really enabled
        self.socket.getsockopt(zmq.EVENTS)

        try:
            request = self.request_queue.get_nowait()
            self.send_request(request)
        except queue.Empty:
            pass

    @Slot()
    def _socket_sub_activity(self):
        if not self.socket_sub.getsockopt(zmq.EVENTS) & zmq.POLLIN:
            return
        self._notifier_sub.setEnabled(False)
        #  Wait for next request from client
        message = self.socket_sub.recv_pyobj()
        cmd = message[0]
        if cmd == "kernel_restarted":
            connection_file = message[1]
            kernel_handler = self._alive_kernel_handlers.get(
                connection_file, None
            )
            if kernel_handler is not None:
                kernel_handler.sig_kernel_restarted.emit()

        elif cmd == "stderr":
            err, connection_file = message
            kernel_handler = self._alive_kernel_handlers.get(
                connection_file, None
            )
            if kernel_handler is not None:
                kernel_handler.handle_stderr(err)

        elif cmd == "stdout":
            out, connection_file = message
            kernel_handler = self._alive_kernel_handlers.get(
                connection_file, None
            )
            if kernel_handler is not None:
                kernel_handler.handle_stdout(out)

        self._notifier_sub.setEnabled(True)
        # This is necessary for some reason.
        # Otherwise the socket only works twice !
        if self.socket_sub.getsockopt(zmq.EVENTS) & zmq.POLLIN:
            self._socket_sub_activity()


class CachedKernelMixin:
    """Cached kernel mixin."""

    def __init__(self):
        super().__init__()
        self._cached_kernel_properties = None

    def close_cached_kernel(self):
        """Close the cached kernel."""
        if self._cached_kernel_properties is None:
            return
        kernel = self._cached_kernel_properties[-1]
        kernel.close(now=True)
        self._cached_kernel_properties = None

    def check_cached_kernel_spec(self, kernel_spec_dict):
        """Test if kernel_spec corresponds to the cached kernel_spec."""
        if self._cached_kernel_properties is None:
            return False
        (
            cached_spec_dict,
            _,
        ) = self._cached_kernel_properties


        if "PYTEST_CURRENT_TEST" in cached_spec_dict["env"]:
            # Make tests faster by using cached kernels
            # hopefully the kernel will never use PYTEST_CURRENT_TEST
            cached_spec_dict["env"][
                "PYTEST_CURRENT_TEST"] = kernel_spec_dict["env"][
                "PYTEST_CURRENT_TEST"
            ]
        return (
            kernel_spec_dict == cached_spec_dict
        )

    def get_cached_kernel(self, kernel_spec_dict, cache=True):
        """Get a new kernel, and cache one for next time."""
        # Cache another kernel for next time.
        new_kernel_handler = self.new_kernel(kernel_spec_dict)

        if not cache:
            # remove/don't use cache if requested
            self.close_cached_kernel()
            return new_kernel_handler

        # Check cached kernel has the same configuration as is being asked
        cached_kernel_handler = None
        if self._cached_kernel_properties is not None:
            cached_kernel_handler = self._cached_kernel_properties[-1]
            if not self.check_cached_kernel_spec(kernel_spec_dict):
                # Close the kernel
                self.close_cached_kernel()
                cached_kernel_handler = None

        # Cache the new kernel
        self._cached_kernel_properties = (
            kernel_spec_dict,
            new_kernel_handler,
        )

        if cached_kernel_handler is None:
            return self.new_kernel(kernel_spec_dict)

        return cached_kernel_handler

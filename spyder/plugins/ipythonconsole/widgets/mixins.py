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

from qtpy.QtCore import QProcess, QSocketNotifier

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
    'kernel_server/external_server',
    'kernel_server/use_ssh',
    'kernel_server/host',
    'kernel_server/port',
    'kernel_server/username',
    'kernel_server/password_auth',
    'kernel_server/keyfile_auth',
    'kernel_server/password',
    'kernel_server/keyfile',
    'kernel_server/passphrase',
]

class KernelConnectorMixin(SpyderConfigurationObserver):
    """Needs https://github.com/jupyter/jupyter_client/pull/835"""
    def __init__(self):
        super().__init__()
        self.options = None
        self.kernel_handler_waitlist = []
        self.request_queue = queue.Queue()
        self.context = zmq.Context()

        self.on_kernel_server_conf_changed()

    @on_conf_change(
        option=KERNEL_SERVER_OPTIONS,
        section='main_interpreter'
    )
    def on_kernel_server_conf_changed(self, option=None, value=None):
        """Start server"""
        options = {
            option: self.get_conf(
                option=option,
                section='main_interpreter')
            for option in KERNEL_SERVER_OPTIONS
        }
        if self.options == options:
            return
        
        self.options = options
        self.hostname = None
        self.sshkey = None
        self.password = None

        is_remote = options['kernel_server/external_server']

        if not is_remote:
            self.start_local_server()
            return
        # Remote server

        remote_port = int(options['kernel_server/port'])
        if not remote_port:
            remote_port = 22
        remote_ip = options['kernel_server/host']


        is_ssh = options['kernel_server/use_ssh']

        if not is_ssh:
            self.connect_socket(f"{remote_ip}:{remote_port}")
            return

        username = options['kernel_server/username']

        self.hostname = f"{username}@{remote_ip}:{remote_port}"

        # Now we deal with ssh
        uses_password = options['kernel_server/password_auth']
        uses_keyfile = options['kernel_server/keyfile_auth']

        if uses_password:
            self.password = options['kernel_server/password']
            self.sshkey = None
        elif uses_keyfile:
            self.password = options['kernel_server/passphrase']
            self.sshkey = options['kernel_server/keyfile']
        else:
            raise NotImplementedError("This should not be possible.")

        local_port = zmqtunnel.select_random_ports(1)
        local_ip = "localhost"
        timeout = 10
        ssh_tunnel(
            local_port, remote_port,
            local_ip, remote_ip,
            self.sshkey, self.password, timeout)
        self.connect_socket(f"{local_ip}:{local_port}")

    def start_local_server(self):
        """Start a server with the current interpreter."""
        port = str(zmqtunnel.select_random_ports(1)[0])
        self.server = QProcess(self)
        self.server.start(
            sys.executable, ["-m", "spyder_kernels_server", port]
            )
        self.connect_socket(f"localhost:{port}")

    def connect_socket(self, hostname):
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{hostname}")
        self._notifier = QSocketNotifier(
            self.socket.getsockopt(zmq.FD),
            QSocketNotifier.Read, self
        )
        self._notifier.activated.connect(self._socket_activity)

    def new_kernel(self, kernel_spec):
        """Get a new kernel"""
        kernel_handler = KernelHandler.new_from_spec(
            kernel_spec=kernel_spec,
            hostname=self.hostname,
            sshkey=self.sshkey,
            password=self.password,
        )
        
        kernel_handler.sig_remote_close.connect(self.request_close)
        self.kernel_handler_waitlist.append(kernel_handler)
        
        
        self.send_request(["open_kernel", kernel_spec])
        
        return kernel_handler
    
    def request_close(self, connection_file):
        self.send_request(["close_kernel", connection_file])
    
    def send_request(self, request):
        
        if self.socket.getsockopt(zmq.EVENTS) & zmq.POLLOUT:
            self.socket.send_pyobj(request)
        else:
            self.request_queue.put(request)
        
    def _socket_activity(self):
        if not self.socket.getsockopt(zmq.EVENTS) & zmq.POLLIN:
            return
        self._notifier.setEnabled(False)
        #  Wait for next request from client
        message = self.socket.recv_pyobj()
        print(message)
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
                kernel_handler.sig_fault.emit(connection_info)
            else:
                kernel_handler.set_connection(
                    connection_file, connection_info,
                    self.hostname,
                    self.sshkey,
                    self.password)
            
        self._notifier.setEnabled(True)
        # This is necessary for some reason.
        # Otherwise the socket only works twice !
        self.socket.getsockopt(zmq.EVENTS)
        
        try:
            request = self.request_queue.get_nowait()
            self.send_request(request)
        except queue.Empty:
            pass


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

    def check_cached_kernel_spec(self, kernel_spec):
        """Test if kernel_spec corresponds to the cached kernel_spec."""
        if self._cached_kernel_properties is None:
            return False
        (
            cached_spec,
            cached_env,
            cached_argv,
            _,
        ) = self._cached_kernel_properties

        # Call interrupt_mode so the dict will be the same
        kernel_spec.interrupt_mode
        cached_spec.interrupt_mode

        if "PYTEST_CURRENT_TEST" in cached_env:
            # Make tests faster by using cached kernels
            # hopefully the kernel will never use PYTEST_CURRENT_TEST
            cached_env["PYTEST_CURRENT_TEST"] = (
                kernel_spec.env["PYTEST_CURRENT_TEST"])
        return (
            cached_spec.__dict__ == kernel_spec.__dict__
            and kernel_spec.argv == cached_argv
            and kernel_spec.env == cached_env
        )

    def get_cached_kernel(self, kernel_spec, cache=True):
        """Get a new kernel, and cache one for next time."""
        # Cache another kernel for next time.
        new_kernel_handler = self.new_kernel(kernel_spec)

        if not cache:
            # remove/don't use cache if requested
            self.close_cached_kernel()
            return new_kernel_handler

        # Check cached kernel has the same configuration as is being asked
        cached_kernel_handler = None
        if self._cached_kernel_properties is not None:
            cached_kernel_handler = self._cached_kernel_properties[-1]
            if not self.check_cached_kernel_spec(kernel_spec):
                # Close the kernel
                self.close_cached_kernel()
                cached_kernel_handler = None

        # Cache the new kernel
        self._cached_kernel_properties = (
            kernel_spec,
            kernel_spec.env,
            kernel_spec.argv,
            new_kernel_handler,
        )

        if cached_kernel_handler is None:
            return self.new_kernel(kernel_spec)

        return cached_kernel_handler

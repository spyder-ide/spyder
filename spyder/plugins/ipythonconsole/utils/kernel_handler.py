# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kernel handler."""

# Standard library imports
import ast
import os
import uuid

# Third-party imports
from qtpy.QtCore import QObject, Signal
from zmq.ssh import tunnel as zmqtunnel

# Local imports
from spyder.api.translations import get_translation
from spyder.plugins.ipythonconsole import (
    SPYDER_KERNELS_MIN_VERSION, SPYDER_KERNELS_MAX_VERSION,
    SPYDER_KERNELS_VERSION, SPYDER_KERNELS_CONDA, SPYDER_KERNELS_PIP)
from spyder_kernels_server.kernel_comm import KernelComm
from spyder_kernels_server.kernel_client import SpyderKernelClient
from spyder.plugins.ipythonconsole.utils.ssh import openssh_tunnel
from spyder.utils.programs import check_version_range


if os.name == "nt":
    ssh_tunnel = zmqtunnel.paramiko_tunnel
else:
    ssh_tunnel = openssh_tunnel


# Localization
_ = get_translation("spyder")

PERMISSION_ERROR_MSG = _(
    "The directory {} is not writable and it is required to create IPython "
    "consoles. Please make it writable."
)

ERROR_SPYDER_KERNEL_VERSION = _(
    "The Python environment or installation whose interpreter is located at"
    "<pre>"
    "    <tt>{0}</tt>"
    "</pre>"
    "doesn't have the right version of <tt>spyder-kernels</tt> installed ({1} "
    "instead of >= {2} and < {3}). Without this module is not possible for "
    "Spyder to create a console for you.<br><br>"
    "You can install it by activating your environment (if necessary) and "
    "then running in a system terminal:"
    "<pre>"
    "    <tt>{4}</tt>"
    "</pre>"
    "or"
    "<pre>"
    "    <tt>{5}</tt>"
    "</pre>"
)

# For Spyder-kernels version < 3.0, where the version and executable cannot be queried
ERROR_SPYDER_KERNEL_VERSION_OLD = _(
    "This Python environment doesn't have the right version of "
    "<tt>spyder-kernels</tt> installed (>= {0} and < {1}). Without this "
    "module is not possible for Spyder to create a console for you.<br><br>"
    "You can install it by activating your environment (if necessary) and "
    "then running in a system terminal:"
    "<pre>"
    "    <tt>{2}</tt>"
    "</pre>"
    "or"
    "<pre>"
    "    <tt>{3}</tt>"
    "</pre>"
)


class KernelConnectionState:
    SpyderKernelReady = 'spyder_kernel_ready'
    IpykernelReady = 'ipykernel_ready'
    Connecting = 'connecting'
    Error = 'error'
    Closed = 'closed'


class KernelHandler(QObject):
    """
    A class to handle the kernel in several ways and store kernel connection
    information.
    """

    sig_fault = Signal(str)
    """
    A fault message was received.
    """

    sig_kernel_is_ready = Signal()
    """
    The kernel is ready.
    """

    sig_kernel_connection_error = Signal()
    """
    The kernel raised an error while connecting.
    """

    sig_request_close = Signal(str)
    """
    This kernel would like to be closed
    """

    def __init__(
        self,
        connection_file,
        kernel_spec=None,
        kernel_client=None,
        known_spyder_kernel=False,
        hostname=None,
        sshkey=None,
        password=None,
    ):
        super().__init__()
        # Connection Informations
        self.connection_file = connection_file
        self.kernel_spec = kernel_spec
        self.kernel_client = kernel_client
        self.known_spyder_kernel = known_spyder_kernel
        self.hostname = hostname
        self.sshkey = sshkey
        self.password = password
        self.kernel_error_message = None
        self.connection_state = KernelConnectionState.Connecting

        # Comm
        self.kernel_comm = KernelComm()
        self.kernel_comm.sig_comm_ready.connect(
            self.handle_comm_ready)

        # Internal
        self._fault_args = None
        self._spyder_kernel_info_uuid = None
        self._shellwidget_connected = False

        # Start kernel
        # self.connect_std_pipes()
        self.kernel_client.start_channels()
        self.check_kernel_info()

    def connect(self):
        """Connect to shellwidget."""
        self._shellwidget_connected = True
        # Emit signal in case the connection is already made
        if self.connection_state in [
                KernelConnectionState.IpykernelReady,
                KernelConnectionState.SpyderKernelReady]:
            self.sig_kernel_is_ready.emit()
        elif self.connection_state == KernelConnectionState.Error:
            self.sig_kernel_connection_error.emit()

        # # Show initial io
        # if self._init_stderr:
        #     self.sig_stderr.emit(self._init_stderr)
        # self._init_stderr = None
        # if self._init_stdout:
        #     self.sig_stdout.emit(self._init_stdout)
        # self._init_stdout = None

    def check_kernel_info(self):
        """Send request to check kernel info."""
        code = "getattr(get_ipython(), '_spyder_kernels_version', False)"
        self.kernel_client.shell_channel.message_received.connect(
            self._dispatch_kernel_info)
        self._spyder_kernel_info_uuid = str(uuid.uuid1())
        self.kernel_client.execute(
            '', silent=True, user_expressions={
                self._spyder_kernel_info_uuid:code })

    def _dispatch_kernel_info(self, msg):
        """Listen for spyder_kernel_info."""
        user_exp = msg['content'].get('user_expressions')
        if not user_exp:
            return
        for expression in user_exp:
            if expression == self._spyder_kernel_info_uuid:
                self.kernel_client.shell_channel.message_received.disconnect(
                    self._dispatch_kernel_info)
                # Process kernel reply
                data = user_exp[expression].get('data')
                if data is not None and 'text/plain' in data:
                    spyder_kernel_info = ast.literal_eval(
                        data['text/plain'])
                    self.check_spyder_kernel_info(spyder_kernel_info)

    def check_spyder_kernel_info(self, spyder_kernel_info):
        """
        Check if the Spyder-kernels version is the right one after receiving it
        from the kernel.

        If the kernel is non-locally managed, check if it is a spyder-kernel.
        """

        if not spyder_kernel_info:
            if self.known_spyder_kernel:
                # spyder-kernels version < 3.0
                self.kernel_error_message = (
                    ERROR_SPYDER_KERNEL_VERSION_OLD.format(
                        SPYDER_KERNELS_MIN_VERSION,
                        SPYDER_KERNELS_MAX_VERSION,
                        SPYDER_KERNELS_CONDA,
                        SPYDER_KERNELS_PIP
                    )
                )
                self.connection_state = KernelConnectionState.Error
                self.known_spyder_kernel = False
                self.sig_kernel_connection_error.emit()
                return

            self.connection_state = KernelConnectionState.IpykernelReady
            self.sig_kernel_is_ready.emit()
            return

        version, pyexec = spyder_kernel_info
        if not check_version_range(version, SPYDER_KERNELS_VERSION):
            # Development versions are acceptable
            if "dev0" not in version:
                self.kernel_error_message = (
                    ERROR_SPYDER_KERNEL_VERSION.format(
                        pyexec,
                        version,
                        SPYDER_KERNELS_MIN_VERSION,
                        SPYDER_KERNELS_MAX_VERSION,
                        SPYDER_KERNELS_CONDA,
                        SPYDER_KERNELS_PIP
                    )
                )
                self.known_spyder_kernel = False
                self.connection_state = KernelConnectionState.Error
                self.sig_kernel_connection_error.emit()
                return

        self.known_spyder_kernel = True

        # Open comm and wait for comm ready reply
        self.kernel_comm.open_comm(self.kernel_client)

    def handle_comm_ready(self):
        """The kernel comm is ready"""
        self.connection_state = KernelConnectionState.SpyderKernelReady
        self.sig_kernel_is_ready.emit()

    @staticmethod
    def tunnel_to_kernel(
        connection_info, hostname, sshkey=None, password=None, timeout=10
    ):
        """
        Tunnel connections to a kernel via ssh.

        Remote ports are specified in the connection info ci.
        """
        lports = zmqtunnel.select_random_ports(5)
        rports = (
            connection_info["shell_port"],
            connection_info["iopub_port"],
            connection_info["stdin_port"],
            connection_info["hb_port"],
            connection_info["control_port"],
        )
        remote_ip = connection_info["ip"]
        for lp, rp in zip(lports, rports):
            ssh_tunnel(lp, rp, hostname, remote_ip, sshkey, password, timeout)
        return tuple(lports)

    @classmethod
    def new_from_spec(
            cls, kernel_spec, connection_file, connection_info,
            hostname=None, sshkey=None, password=None
    ):
        """
        Create a new kernel.
        """
        kernel_client = SpyderKernelClient()
        kernel_client.load_connection_info(connection_info)
        kernel_client = cls.tunnel_kernel_client(
            kernel_client,
            hostname,
            sshkey,
            password
            )

        # Increase time (in seconds) to detect if a kernel is alive.
        # See spyder-ide/spyder#3444.
        kernel_client.hb_channel.time_to_dead = 25.0

        return cls(
            connection_file=connection_file,
            kernel_spec=kernel_spec,
            kernel_client=kernel_client,
            known_spyder_kernel=True,
            hostname=hostname,
            sshkey=sshkey,
            password=password,
        )

    @classmethod
    def from_connection_file(
        cls, connection_file, hostname=None, sshkey=None, password=None
    ):
        """Create kernel for given connection file."""
        kernel_client = SpyderKernelClient(
            connection_file=connection_file
        )

        # This is needed for issue spyder-ide/spyder#9304.
        try:
            kernel_client.load_connection_file()
        except Exception as e:
            raise RuntimeError(
                _(
                    "An error occurred while trying to load "
                    "the kernel connection file. The error "
                    "was:\n\n"
                )
                + str(e)
            )

        kernel_client = cls.tunnel_kernel_client(
            kernel_client,
            hostname,
            sshkey,
            password
            )

        return cls(
            connection_file,
            hostname=hostname,
            sshkey=sshkey,
            password=password,
            kernel_client=kernel_client
        )

    @classmethod
    def tunnel_kernel_client(cls, kernel_client, hostname, sshkey, password):
        """Create kernel client."""
        if hostname is not None:
            try:
                connection_info = dict(
                    ip=kernel_client.ip,
                    shell_port=kernel_client.shell_port,
                    iopub_port=kernel_client.iopub_port,
                    stdin_port=kernel_client.stdin_port,
                    hb_port=kernel_client.hb_port,
                    control_port=kernel_client.control_port,
                )

                (
                    kernel_client.shell_port,
                    kernel_client.iopub_port,
                    kernel_client.stdin_port,
                    kernel_client.hb_port,
                    kernel_client.control_port,
                ) = cls.tunnel_to_kernel(
                    connection_info, hostname, sshkey, password
                )
            except Exception as e:
                raise RuntimeError(
                    _("Could not open ssh tunnel. The error was:\n\n")
                    + str(e)
                )
        return kernel_client

    def close(self, shutdown_kernel=True, now=False):
        """Close kernel"""
        self.close_comm()

        if shutdown_kernel and self.kernel_spec is not None:
            self.sig_request_close.emit(self.connection_file)

        if (
            self.kernel_client is not None
            and self.kernel_client.channels_running
        ):
            self.kernel_client.stop_channels()

    def after_shutdown(self):
        """Cleanup after shutdown"""
        self.close_std_threads()
        self.kernel_comm.remove(only_closing=True)

    def copy(self):
        """Copy kernel."""
        # Copy kernel infos

        # Get new kernel_client
        kernel_client = self.init_kernel_client(
            self.connection_file,
            self.hostname,
            self.sshkey,
            self.password,
        )

        return self.__class__(
            connection_file=self.connection_file,
            kernel_spec=self.kernel_spec,
            known_spyder_kernel=self.known_spyder_kernel,
            hostname=self.hostname,
            sshkey=self.sshkey,
            password=self.password,
            kernel_client=kernel_client,
        )

    def faulthandler_setup(self, args):
        """Setup faulthandler"""
        self._fault_args = args

    def enable_faulthandler(self):
        """Enable faulthandler"""
        # To display faulthandler
        self.kernel_comm.remote_call(
            callback=self.faulthandler_setup
        ).enable_faulthandler()

    def poll_fault_text(self):
        """Get a fault from a previous session."""
        if self._fault_args is None:
            return
        self.kernel_comm.remote_call(
            callback=self.emit_fault_text
        ).get_fault_text(*self._fault_args)
        self._fault_args = None

    def emit_fault_text(self, fault):
        """Emit fault text"""
        if not fault:
            return
        self.sig_fault.emit(fault)

    def fault_filename(self):
        """Get fault filename."""
        if not self._fault_args:
            return
        return self._fault_args[0]

    def close_comm(self):
        """Close comm"""
        self.connection_state = KernelConnectionState.Closed
        self.kernel_comm.close()

    def reopen_comm(self):
        """Reopen comm (following a crash)"""
        self.kernel_comm.remove()
        self.connection_state = KernelConnectionState.Connecting
        self.kernel_comm.open_comm(self.kernel_client)

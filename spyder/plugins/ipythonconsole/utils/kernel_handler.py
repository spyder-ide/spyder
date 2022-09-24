# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kernel handler."""

# Standard library imports
import os
import os.path as osp
import re
from subprocess import PIPE
from threading import Lock
import uuid

# Third-party imports
from jupyter_core.paths import jupyter_runtime_dir
from qtpy.QtCore import QObject, QThread, Signal
from zmq.ssh import tunnel as zmqtunnel

# Local imports
from spyder.api.translations import get_translation
from spyder.plugins.ipythonconsole.utils.manager import SpyderKernelManager
from spyder.plugins.ipythonconsole.utils.client import SpyderKernelClient
from spyder.plugins.ipythonconsole.utils.ssh import openssh_tunnel


# Localization
_ = get_translation("spyder")

PERMISSION_ERROR_MSG = _(
    "The directory {} is not writable and it is required to create IPython "
    "consoles. Please make it writable."
)

if os.name == "nt":
    ssh_tunnel = zmqtunnel.paramiko_tunnel
else:
    ssh_tunnel = openssh_tunnel


class StdThread(QThread):
    """Poll for changes in std buffers."""
    sig_out = Signal(str)

    def __init__(self, parent, std_buffer):
        super().__init__(parent)
        self._std_buffer = std_buffer

    def run(self):
        txt = True
        while txt:
            txt = self._std_buffer.read1()
            if txt:
                self.sig_out.emit(txt.decode())


class KernelHandler(QObject):
    """
    A class to handle the kernel in several ways and store kernel connection
    information.
    """

    sig_stdout = Signal(str)
    sig_stderr = Signal(str)
    sig_fault = Signal(str)

    def __init__(
        self,
        connection_file,
        kernel_manager=None,
        kernel_client=None,
        known_spyder_kernel=False,
        hostname=None,
        sshkey=None,
        password=None,
    ):
        super().__init__()
        # Connection Informations
        self.connection_file = connection_file
        self.kernel_manager = kernel_manager
        self.kernel_client = kernel_client
        self.known_spyder_kernel = known_spyder_kernel
        self.hostname = hostname
        self.sshkey = sshkey
        self.password = password

        # Comm
        self.kernel_comm = None

        # Internal
        self.shutdown_thread = None
        self._shutdown_lock = Lock()
        self._stdout_thread = None
        self._stderr_thread = None
        self._fault_args = None

        self.connect_std_pipes()

    def connect_std_pipes(self):
        """Connect to std pipes."""
        self.close_std_threads()
        # Connect new threads
        if self.kernel_manager is None:
            return

        stdout = self.kernel_manager.provisioner.process.stdout
        stderr = self.kernel_manager.provisioner.process.stderr

        if stdout:
            self._stdout_thread = StdThread(self, stdout)
            self._stdout_thread.sig_out.connect(self.sig_stdout)
            self._stdout_thread.start()
        if stderr:
            self._stderr_thread = StdThread(self, stderr)
            self._stderr_thread.sig_out.connect(self.sig_stderr)
            self._stderr_thread.start()

    def disconnect_std_pipes(self):
        """Disconnect old std pipes."""
        if self._stdout_thread:
            self._stdout_thread.sig_out.disconnect(self.sig_stdout)
        if self._stderr_thread:
            self._stderr_thread.sig_out.disconnect(self.sig_stderr)

    def close_std_threads(self):
        """Close std threads."""
        if self._stdout_thread is not None:
            self._stdout_thread.wait()
            self._stdout_thread = None
        if self._stderr_thread is not None:
            self._stderr_thread.wait()
            self._stderr_thread = None

    @staticmethod
    def new_connection_file():
        """
        Generate a new connection file

        Taken from jupyter_client/console_app.py
        Licensed under the BSD license
        """
        # Check if jupyter_runtime_dir exists (Spyder addition)
        if not osp.isdir(jupyter_runtime_dir()):
            try:
                os.makedirs(jupyter_runtime_dir())
            except (IOError, OSError):
                return None
        cf = ""
        while not cf:
            ident = str(uuid.uuid4()).split("-")[-1]
            cf = os.path.join(jupyter_runtime_dir(), "kernel-%s.json" % ident)
            cf = cf if not os.path.exists(cf) else ""
        return cf

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
    def new_from_spec(cls, kernel_spec):
        """
        Create a new kernel.

        Might raise all kinds of exceptions
        """
        connection_file = cls.new_connection_file()
        if connection_file is None:
            raise RuntimeError(
                PERMISSION_ERROR_MSG.format(jupyter_runtime_dir())
            )

        # Kernel manager
        kernel_manager = SpyderKernelManager(
            connection_file=connection_file,
            config=None,
            autorestart=True,
        )

        kernel_manager._kernel_spec = kernel_spec

        kernel_manager.start_kernel(
            stderr=PIPE,
            stdout=PIPE,
            env=kernel_spec.env,
        )

        # Kernel client
        kernel_client = kernel_manager.client()

        # Increase time (in seconds) to detect if a kernel is alive.
        # See spyder-ide/spyder#3444.
        kernel_client.hb_channel.time_to_dead = 25.0

        return cls(
            connection_file=connection_file,
            kernel_manager=kernel_manager,
            kernel_client=kernel_client,
            known_spyder_kernel=True,
        )

    @classmethod
    def from_connection_file(
        cls, connection_file, hostname=None, sshkey=None, password=None
    ):
        """Create kernel for given connection file."""
        new_kernel = cls(
            connection_file,
            hostname=hostname,
            sshkey=sshkey,
            password=password,
        )
        # Get new kernel_client
        new_kernel.init_kernel_client()
        return new_kernel

    def init_kernel_client(self):
        """Create kernel client."""
        kernel_client = SpyderKernelClient(
            connection_file=self.connection_file
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

        if self.hostname is not None:
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
                ) = self.tunnel_to_kernel(
                    connection_info, self.hostname, self.sshkey, self.password
                )
            except Exception as e:
                raise RuntimeError(
                    _("Could not open ssh tunnel. The error was:\n\n")
                    + str(e)
                )
        self.kernel_client = kernel_client

    def close(self, shutdown_kernel=True, now=False):
        """Close kernel"""
        if self.kernel_comm is not None:
            self.kernel_comm.close()

        if shutdown_kernel and self.kernel_manager is not None:
            km = self.kernel_manager
            km.stop_restarter()

            self.disconnect_std_pipes()

            if now:
                km.shutdown_kernel(now=True)
                self.after_shutdown()
            else:
                shutdown_thread = QThread(None)
                shutdown_thread.run = self._thread_shutdown_kernel
                shutdown_thread.start()
                shutdown_thread.finished.connect(self.after_shutdown)
                self.shutdown_thread = shutdown_thread

        if (
            self.kernel_client is not None
            and self.kernel_client.channels_running
        ):
            self.kernel_client.stop_channels()

    def after_shutdown(self):
        """Cleanup after shutdown"""
        self.close_std_threads()
        if self.kernel_comm is not None:
            self.kernel_comm.remove(only_closing=True)
        self.shutdown_thread = None

    def _thread_shutdown_kernel(self):
        """Shutdown kernel."""
        with self._shutdown_lock:
            # Avoid calling shutdown_kernel on the same manager twice
            # from different threads to avoid crash.
            if self.kernel_manager.shutting_down:
                return
            self.kernel_manager.shutting_down = True
        try:
            self.kernel_manager.shutdown_kernel()
        except Exception:
            # kernel was externally killed
            pass

    def wait_shutdown_thread(self):
        """Wait shutdown thread."""
        thread = self.shutdown_thread
        if thread is None:
            return
        if thread.isRunning():
            try:
                thread.kernel_manager._kill_kernel()
            except Exception:
                pass
            thread.quit()
            thread.wait()

    def copy(self):
        """Copy kernel."""
        # Copy kernel infos
        new_kernel = self.__class__(
            connection_file=self.connection_file,
            kernel_manager=self.kernel_manager,
            known_spyder_kernel=self.known_spyder_kernel,
            hostname=self.hostname,
            sshkey=self.sshkey,
            password=self.password,
        )
        # Get new kernel_client
        new_kernel.init_kernel_client()
        return new_kernel

    def open_comm(self, kernel_comm):
        """Open kernel comm"""
        kernel_comm.open_comm(self.kernel_client)
        self.kernel_comm = kernel_comm

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

    def restart_kernel(self):
        """Restart kernel."""
        if self.kernel_manager is None:
            return
        self.kernel_manager.restart_kernel(
            stderr=PIPE,
            stdout=PIPE,
        )

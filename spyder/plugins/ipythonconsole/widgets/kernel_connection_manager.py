# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""Kernel connection manager."""

# Standard library imports
import os
import os.path as osp
from threading import Lock
import uuid

# Third-party imports
from jupyter_core.paths import jupyter_runtime_dir
from qtpy.QtCore import QThread
from zmq.ssh import tunnel as zmqtunnel

# Local imports
from spyder.api.translations import get_translation
from spyder.plugins.ipythonconsole.utils.manager import SpyderKernelManager
from spyder.plugins.ipythonconsole.utils.client import SpyderKernelClient
from spyder.plugins.ipythonconsole.utils.ssh import openssh_tunnel
from spyder.plugins.ipythonconsole.utils.stdfile import StdFile


# Localization
_ = get_translation("spyder")
PERMISSION_ERROR_MSG = _(
    "The directory {} is not writable and it is "
    "required to create IPython consoles. Please "
    "make it writable."
)

if os.name == "nt":
    ssh_tunnel = zmqtunnel.paramiko_tunnel
else:
    ssh_tunnel = openssh_tunnel


class KernelConnection:
    """A class to store kernel connection informations."""

    # Class array of shutdown threads
    shutdown_thread_list = []

    def __init__(
        self,
        connection_file,
        kernel_manager=None,
        kernel_client=None,
        stderr_obj=None,
        stdout_obj=None,
        fault_obj=None,
        known_spyder_kernel=False,
        hostname=None,
        sshkey=None,
        password=None,
    ):
        # Connection Informations
        self.connection_file = connection_file
        self.kernel_manager = kernel_manager
        self.kernel_client = kernel_client
        self.stderr_obj = stderr_obj
        self.stdout_obj = stdout_obj
        self.fault_obj = fault_obj
        self.known_spyder_kernel = known_spyder_kernel
        self.hostname = hostname
        self.sshkey = sshkey
        self.password = password
        # Comm
        self.kernel_comm = None
        # Internal
        self._shutdown_lock = Lock()

    @classmethod
    def prune_shutdown_thread_list(cls):
        """Remove shutdown threads."""
        pruned_shutdown_thread_list = []
        for t in cls.shutdown_thread_list:
            try:
                if t.isRunning():
                    pruned_shutdown_thread_list.append(t)
            except RuntimeError:
                pass
        cls.shutdown_thread_list = pruned_shutdown_thread_list

    @classmethod
    def wait_all_shutdown(cls):
        """Wait for shutdown to finish."""
        for thread in cls.shutdown_thread_list:
            if thread.isRunning():
                try:
                    thread.kernel_manager._kill_kernel()
                except Exception:
                    pass
                thread.quit()
                thread.wait()
        cls.shutdown_thread_list = []

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

        stderr_obj = StdFile(connection_file, ".stderr")
        stdout_obj = StdFile(connection_file, ".stdout")
        fault_obj = StdFile(connection_file, ".fault")

        # Kernel manager
        kernel_manager = SpyderKernelManager(
            connection_file=connection_file,
            config=None,
            autorestart=True,
        )

        kernel_manager._kernel_spec = kernel_spec

        kernel_manager.start_kernel(
            stderr=stderr_obj.handle,
            stdout=stdout_obj.handle,
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
            stderr_obj=stderr_obj,
            stdout_obj=stdout_obj,
            fault_obj=fault_obj,
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
        if shutdown_kernel and self.kernel_manager is not None:
            km = self.kernel_manager
            km.stop_restarter()
            if now:
                km.shutdown_kernel(now=True)
            else:
                shutdown_thread = QThread(None)
                shutdown_thread.kernel_manager = km
                shutdown_thread.run = self._thread_shutdown_kernel
                self.shutdown_thread_list.append(shutdown_thread)
                shutdown_thread.start()
                self.prune_shutdown_thread_list()
        if self.kernel_comm is not None:
            self.kernel_comm.close()
            self.kernel_comm.remove()
        if (
            self.kernel_client is not None
            and self.kernel_client.channels_running
        ):
            self.kernel_client.stop_channels()

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

        # Copy std file
        if self.stderr_obj is not None:
            new_kernel.stderr_obj = self.stderr_obj.copy()
        if self.stdout_obj is not None:
            new_kernel.stdout_obj = self.stdout_obj.copy()
        if self.fault_obj is not None:
            new_kernel.fault_obj = self.fault_obj.copy()

        # Get new kernel_client
        new_kernel.init_kernel_client()
        return new_kernel

    def remove_files(self):
        """Remove std files."""
        if self.stderr_obj is not None:
            self.stderr_obj.remove()
        if self.stdout_obj is not None:
            self.stdout_obj.remove()
        if self.fault_obj is not None:
            self.fault_obj.remove()

    def open_comm(self, kernel_comm):
        """Open kernel comm"""
        kernel_comm.open_comm(self.kernel_client)
        self.kernel_comm = kernel_comm


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
        kernel.remove_files()
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
        return (
            cached_spec.__dict__ == kernel_spec.__dict__
            and kernel_spec.argv == cached_argv
            and kernel_spec.env == cached_env
        )

    def get_cached_kernel(self, kernel_spec, cache=True):
        """Get a new kernel, and cache one for next time."""
        # Cache another kernel for next time.
        new_kernel = KernelConnection.new_from_spec(kernel_spec)

        if not cache:
            # remove/don't use cache if requested
            self.close_cached_kernel()
            return new_kernel

        # Check cached kernel has the same configuration as is being asked
        cached_kernel = None
        if self._cached_kernel_properties is not None:
            cached_kernel = self._cached_kernel_properties[-1]
            if not self.check_cached_kernel_spec(kernel_spec):
                # Close the kernel
                self.close_cached_kernel()
                cached_kernel = None

        # Cache the new kernel
        self._cached_kernel_properties = (
            kernel_spec,
            kernel_spec.env,
            kernel_spec.argv,
            new_kernel,
        )

        if cached_kernel is None:
            return KernelConnection.new_from_spec(kernel_spec)

        return cached_kernel

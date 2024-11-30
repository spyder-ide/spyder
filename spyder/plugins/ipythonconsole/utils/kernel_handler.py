# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kernel handler."""

# Standard library imports
import json
import os
import os.path as osp
from subprocess import PIPE
from threading import Lock
import uuid

# Third-party imports
from jupyter_core.paths import jupyter_runtime_dir
from qtpy.QtCore import QObject, QThread, Signal, Slot

# Local imports
from spyder.api.translations import _
from spyder.config.base import running_under_pytest
from spyder.plugins.ipythonconsole import (
    SPYDER_KERNELS_MIN_VERSION,
    SPYDER_KERNELS_MAX_VERSION,
    SPYDER_KERNELS_VERSION,
    SPYDER_KERNELS_CONDA,
    SPYDER_KERNELS_PIP,
    SpyderKernelError,
)
from spyder.plugins.ipythonconsole.comms.kernelcomm import KernelComm
from spyder.plugins.ipythonconsole.utils.manager import SpyderKernelManager
from spyder.plugins.ipythonconsole.utils.client import SpyderKernelClient
from spyder.utils.programs import check_version_range


PERMISSION_ERROR_MSG = _(
    "The directory <tt>{}</tt> is not writable and it is required to create "
    "IPython consoles. Please make it writable."
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
    SpyderKernelWaitComm = "spyder_kernel_wait_comm"
    SpyderKernelReady = "spyder_kernel_ready"
    IpykernelReady = "ipykernel_ready"
    Connecting = "connecting"
    Error = "error"
    Closed = "closed"
    Crashed = "crashed"


class StdThread(QThread):
    """Poll for changes in std buffers."""

    sig_out = Signal(str)

    def __init__(self, parent, std_buffer):
        super().__init__(parent)
        self._std_buffer = std_buffer
        self._closing = False

    def run(self):
        txt = True
        while txt:
            txt = self._std_buffer.read1()
            if txt:
                try:
                    txt = txt.decode()
                except UnicodeDecodeError:
                    txt = str(txt)
                self.sig_out.emit(txt)


class KernelHandler(QObject):
    """
    A class to handle the kernel in several ways and store kernel connection
    information.
    """

    sig_stdout = Signal(str)
    """
    A stdout message was received on the process stdout.
    """

    sig_stderr = Signal(str)
    """
    A stderr message was received on the process stderr.
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

    _shutdown_thread_list = []
    """List of running shutdown threads"""

    _shutdown_thread_list_lock = Lock()
    """
    Lock to add threads to _shutdown_thread_list or clear that list.
    """

    def __init__(
        self,
        connection_file,
        kernel_manager=None,
        kernel_client=None,
        known_spyder_kernel=False,
        hostname=None,
        sshkey=None,
        password=None,
        ssh_connection=None,
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
        self.ssh_connection = ssh_connection
        self.kernel_error_message = None
        self.connection_state = KernelConnectionState.Connecting

        # Comm
        self.kernel_comm = KernelComm()
        self.kernel_comm.sig_comm_ready.connect(self.handle_comm_ready)

        # Internal
        self._shutdown_lock = Lock()
        self._stdout_thread = None
        self._stderr_thread = None
        self._fault_args = None
        self._init_stderr = ""
        self._init_stdout = ""
        self._shellwidget_connected = False
        self._comm_ready_received = False

        # Start kernel
        self.kernel_client.sig_spyder_kernel_info.connect(
            self.check_spyder_kernel_info
        )
        self.connect_std_pipes()
        self.kernel_client.start_channels()

        # Open comm and wait for comm ready reply.
        # It only works for spyder-kernels, but this is the majority of cases.
        # For ipykernels, this does nothing.
        self.kernel_comm.open_comm(self.kernel_client)

    @property
    def connection_info(self):
        """Get connection info."""
        connection_info = self.kernel_client.get_connection_info()
        connection_info["key"] = connection_info["key"].decode()
        return connection_info

    def connect_(self):
        """Connect to shellwidget."""
        self._shellwidget_connected = True
        # Emit signal in case the connection is already made
        if self.connection_state in [
            KernelConnectionState.IpykernelReady,
            KernelConnectionState.SpyderKernelReady
        ]:
            # This is necessary for systems in which the kernel takes too much
            # time to start because in that case its heartbeat is not detected
            # as beating at this point.
            # Fixes spyder-ide/spyder#22179
            self.kernel_client.hb_channel._beating = True
            self.sig_kernel_is_ready.emit()
        elif self.connection_state == KernelConnectionState.Error:
            self.sig_kernel_connection_error.emit()

        # Show initial io
        if self._init_stderr:
            self.sig_stderr.emit(self._init_stderr)
        self._init_stderr = None
        if self._init_stdout:
            self.sig_stdout.emit(self._init_stdout)
        self._init_stdout = None

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
                        SPYDER_KERNELS_PIP,
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
                self.kernel_error_message = ERROR_SPYDER_KERNEL_VERSION.format(
                    pyexec,
                    version,
                    SPYDER_KERNELS_MIN_VERSION,
                    SPYDER_KERNELS_MAX_VERSION,
                    SPYDER_KERNELS_CONDA,
                    SPYDER_KERNELS_PIP,
                )
                self.known_spyder_kernel = False
                self.connection_state = KernelConnectionState.Error
                self.sig_kernel_connection_error.emit()
                return

        self.known_spyder_kernel = True
        self.connection_state = KernelConnectionState.SpyderKernelWaitComm
        if self._comm_ready_received:
            self.handle_comm_ready()

    def handle_comm_ready(self):
        """The kernel comm is ready"""
        self._comm_ready_received = True
        if self.connection_state in [
            KernelConnectionState.SpyderKernelWaitComm,
            KernelConnectionState.Crashed,
        ]:
            # This is necessary for systems in which the kernel takes too much
            # time to start because in that case its heartbeat is not detected
            # as beating at this point.
            # Fixes spyder-ide/spyder#22179
            self.kernel_client.hb_channel._beating = True
            self.connection_state = KernelConnectionState.SpyderKernelReady
            self.sig_kernel_is_ready.emit()

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
            self._stdout_thread.sig_out.connect(self.handle_stdout)
            self._stdout_thread.start()
        if stderr:
            self._stderr_thread = StdThread(self, stderr)
            self._stderr_thread.sig_out.connect(self.handle_stderr)
            self._stderr_thread.start()

    def disconnect_std_pipes(self):
        """Disconnect old std pipes."""
        if self._stdout_thread and not self._stdout_thread._closing:
            self._stdout_thread.sig_out.disconnect(self.handle_stdout)
            self._stdout_thread._closing = True
        if self._stderr_thread and not self._stderr_thread._closing:
            self._stderr_thread.sig_out.disconnect(self.handle_stderr)
            self._stderr_thread._closing = True

    def close_std_threads(self):
        """Close std threads."""
        if self._stdout_thread is not None:
            self._stdout_thread.wait()
            self._stdout_thread = None
        if self._stderr_thread is not None:
            self._stderr_thread.wait()
            self._stderr_thread = None

    @Slot(str)
    def handle_stderr(self, err):
        """Handle stderr"""
        if self._shellwidget_connected:
            self.sig_stderr.emit(err)
        else:
            self._init_stderr += err

    @Slot(str)
    def handle_stdout(self, out):
        """Handle stdout"""
        if self._shellwidget_connected:
            self.sig_stdout.emit(out)
        else:
            self._init_stdout += out

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

    @classmethod
    def new_from_spec(cls, kernel_spec):
        """
        Create a new kernel.

        Might raise all kinds of exceptions
        """
        connection_file = cls.new_connection_file()
        if connection_file is None:
            raise SpyderKernelError(
                PERMISSION_ERROR_MSG.format(jupyter_runtime_dir())
            )

        # Kernel manager
        kernel_manager = SpyderKernelManager(
            connection_file=connection_file,
            config=None,
            autorestart=True,
        )

        kernel_manager._kernel_spec = kernel_spec

        try:
            kernel_manager.start_kernel(
                stderr=PIPE,
                stdout=PIPE,
                env=kernel_spec.env,
            )
        except PermissionError:
            # Show a nice error message when jupyter_runtime_dir is not
            # writable.
            # Fixes spyder-ide/spyder#23124
            raise SpyderKernelError(
                PERMISSION_ERROR_MSG.format(jupyter_runtime_dir())
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
    def from_connection_info(
        cls,
        connection_info,
        hostname=None,
        sshkey=None,
        password=None,
        ssh_connection=None,
    ):
        """Create kernel for given connection info."""
        new_connection_file = cls.new_connection_file()
        with open(new_connection_file, "w") as f:
            json.dump(connection_info, f)

        return cls(
            new_connection_file,
            kernel_client=cls.init_kernel_client(
                new_connection_file,
                hostname,
                sshkey,
                password,
                ssh_connection,
            ),
        )

    @classmethod
    def from_connection_file(
        cls,
        connection_file,
        hostname=None,
        sshkey=None,
        password=None,
        ssh_connection=None,
    ):
        """Create kernel for given connection file."""
        return cls(
            connection_file,
            hostname=hostname,
            sshkey=sshkey,
            password=password,
            kernel_client=cls.init_kernel_client(
                connection_file,
                hostname,
                sshkey,
                password,
                ssh_connection,
            ),
        )

    @staticmethod
    def init_kernel_client(
        connection_file,
        hostname,
        sshkey,
        password,
        ssh_connection,
    ):
        """Create kernel client."""
        kernel_client = SpyderKernelClient(connection_file=connection_file)

        # This is needed for issue spyder-ide/spyder#9304.
        try:
            kernel_client.load_connection_file()
        except Exception as e:
            raise SpyderKernelError(
                _(
                    "An error occurred while trying to load "
                    "the kernel connection file. The error "
                    "was:\n\n"
                )
                + f"<tt>{str(e)}</tt>"
            )

        if hostname is not None or ssh_connection is not None:
            kernel_client.tunnel_to_kernel(
                hostname=hostname,
                sshkey=sshkey,
                password=password,
                ssh_connection=ssh_connection,
            )

        return kernel_client

    def close(self, shutdown_kernel=True, now=False):
        """Close kernel"""
        self.close_comm()
        if shutdown_kernel and self.kernel_manager is not None:
            km = self.kernel_manager
            km.stop_restarter()
            self.disconnect_std_pipes()

            # This is probably necessary due to a weird interaction between
            # `conda run --no-capture-output` and pytest capturing output
            # facilities.
            if now or running_under_pytest():
                km.shutdown_kernel(now=True)
                self.after_shutdown()
            else:
                shutdown_thread = QThread(None)
                shutdown_thread.run = self._thread_shutdown_kernel
                shutdown_thread.start()
                shutdown_thread.finished.connect(self.after_shutdown)
                with self._shutdown_thread_list_lock:
                    self._shutdown_thread_list.append(shutdown_thread)

        if (
            self.kernel_client is not None
            and self.kernel_client.channels_running
        ):
            self.kernel_client.stop_channels()

    def after_shutdown(self):
        """Cleanup after shutdown"""
        self.close_std_threads()
        self.kernel_comm.remove(only_closing=True)

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

    @classmethod
    def wait_all_shutdown_threads(cls):
        """Wait shutdown thread."""
        with cls._shutdown_thread_list_lock:
            for thread in cls._shutdown_thread_list:
                if thread.isRunning():
                    try:
                        thread.kernel_manager._kill_kernel()
                    except Exception:
                        pass
                    thread.quit()
                    thread.wait()
            cls._shutdown_thread_list = []

    def copy(self):
        """Copy kernel."""
        # Copy kernel infos

        # Get new kernel_client
        kernel_client = self.init_kernel_client(
            self.connection_file,
            self.hostname,
            self.sshkey,
            self.password,
            self.ssh_connection,
        )

        return self.__class__(
            connection_file=self.connection_file,
            kernel_manager=self.kernel_manager,
            known_spyder_kernel=self.known_spyder_kernel,
            hostname=self.hostname,
            sshkey=self.sshkey,
            password=self.password,
            ssh_connection=self.ssh_connection,
            kernel_client=kernel_client,
        )

    def faulthandler_setup(self, args):
        """Setup faulthandler"""
        self._fault_args = args

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
        self.connection_state = KernelConnectionState.Crashed
        self.kernel_comm.open_comm(self.kernel_client)

    def reconnect_kernel(self):
        """Kernel restarted successfully, so reconnect to it."""
        self.reopen_comm()
        self.disconnect_std_pipes()
        self.connect_std_pipes()

    def set_time_to_dead(self, time_to_dead):
        """Set time to detect if the kernel is dead in seconds."""
        if self.kernel_client is not None:
            self.kernel_client.hb_channel.time_to_dead = time_to_dead

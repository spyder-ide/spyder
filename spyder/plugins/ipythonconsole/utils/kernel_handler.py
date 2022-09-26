# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kernel handler."""

# Standard library imports
import ast
import os
import os.path as osp
import re
from threading import Lock
import uuid

# Third-party imports
from jupyter_core.paths import jupyter_runtime_dir
from qtpy.QtCore import QThread, Signal, QObject
from zmq.ssh import tunnel as zmqtunnel

# Local imports
from spyder.api.translations import get_translation
from spyder.plugins.ipythonconsole.comms.kernelcomm import KernelComm
from spyder.plugins.ipythonconsole.utils.manager import SpyderKernelManager
from spyder.plugins.ipythonconsole.utils.client import SpyderKernelClient
from spyder.plugins.ipythonconsole.utils.ssh import openssh_tunnel
from spyder.plugins.ipythonconsole.utils.stdfile import StdFile


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


class KernelHandler(QObject):
    """
    A class to handle the kernel in several ways and store kernel connection
    information.
    """

    sig_kernel_info = Signal(object)

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
        super().__init__()
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
        self.shutdown_thread = None
        self._shutdown_lock = Lock()

        # Check kernel version
        self.spyder_kernel_info = None
        kernel_client.start_channels()
        code = "getattr(get_ipython(), '_spyder_kernels_version', False)"
        kernel_client.shell_channel.message_received.connect(self._dispatch)
        self._local_uuid = str(uuid.uuid1())
        kernel_client.execute(
            '', silent=True, user_expressions={ self._local_uuid:code })

    def _dispatch(self, msg):
        """Listen for spyder_kernel_info."""
        user_exp = msg['content'].get('user_expressions')
        if not user_exp:
            return
        for expression in user_exp:
            if expression == self._local_uuid:
                self.kernel_client.shell_channel.message_received.disconnect(
                    self._dispatch)
                # Process kernel reply
                data = user_exp[expression].get('data')
                if data is not None and 'text/plain' in data:
                    self.spyder_kernel_info = ast.literal_eval(
                        data['text/plain'])
                    self.sig_kernel_info.emit(self.spyder_kernel_info)


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
        return cls(
            connection_file,
            hostname=hostname,
            sshkey=sshkey,
            password=password,
            kernel_client=cls.init_kernel_client(
                connection_file,
                hostname,
                sshkey,
                password
            )
        )

    @classmethod
    def init_kernel_client(cls, connection_file, hostname, sshkey, password):
        """Create kernel client."""
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
        if self.kernel_comm is not None:
            self.kernel_comm.close()

        if shutdown_kernel and self.kernel_manager is not None:
            km = self.kernel_manager
            km.stop_restarter()

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

        # Copy std file
        stderr_obj = None
        if self.stderr_obj is not None:
            stderr_obj = self.stderr_obj.copy()
        stdout_obj = None
        if self.stdout_obj is not None:
            stdout_obj = self.stdout_obj.copy()
        fault_obj = None
        if self.fault_obj is not None:
            fault_obj = self.fault_obj.copy()

        # Get new kernel_client
        kernel_client = self.init_kernel_client(
            self.connection_file,
            self.hostname,
            self.sshkey,
            self.password,
        )

        return self.__class__(
            connection_file=self.connection_file,
            kernel_manager=self.kernel_manager,
            known_spyder_kernel=self.known_spyder_kernel,
            hostname=self.hostname,
            sshkey=self.sshkey,
            password=self.password,
            stderr_obj=stderr_obj,
            stdout_obj=stdout_obj,
            fault_obj=fault_obj,
            kernel_client=kernel_client,
        )

    def remove_files(self):
        """Remove std files."""
        for obj in [self.stderr_obj, self.stderr_obj, self.fault_obj]:
            if obj is not None:
                obj.remove()

    def get_kernel_comm(self, handlers):
        """Open kernel comm"""
        if self.kernel_comm is None:
            self.kernel_comm = KernelComm()
            for request_id in handlers:
                self.kernel_comm.register_call_handler(
                    request_id, handlers[request_id])
            self.kernel_comm.open_comm(self.kernel_client)
        return self.kernel_comm

    def replace_std_files(self):
        """Replace std files."""
        for obj in [self.stderr_obj, self.stderr_obj, self.fault_obj]:
            if obj is None:
                continue
            obj.remove()
            fn = obj.filename
            m = re.match(r"(.+_)(\d+)(.[a-z]+)", fn)
            if m:
                # Already a replaced file
                path, n, ext = m.groups()
                obj.filename = path + str(1 + int(n)) + ext
                continue
            m = re.match(r"(.+)(.[a-z]+)", fn)
            if m:
                # First replaced file
                path, ext = m.groups()
                obj.filename = path + "_1" + ext
                continue
            # No extension, should not happen
            obj.filename += "_1"

    def get_fault_filename(self):
        """Get faulthandler filename"""
        if self.fault_obj is None:
            return
        return self.fault_obj.filename

    def get_fault_text(self):
        """Get a fault from a previous session."""

        if self.fault_obj is None:
            return
        fault = self.fault_obj.get_contents()
        if not fault:
            return

        thread_regex = (
            r"(Current thread|Thread) "
            r"(0x[\da-f]+) \(most recent call first\):"
            r"(?:.|\r\n|\r|\n)+?(?=Current thread|Thread|\Z)")
        # Keep line for future improvments
        # files_regex = r"File \"([^\"]+)\", line (\d+) in (\S+)"

        main_re = "Main thread id:(?:\r\n|\r|\n)(0x[0-9a-f]+)"
        main_id = 0
        for match in re.finditer(main_re, fault):
            main_id = int(match.group(1), base=16)

        system_re = ("System threads ids:"
                     "(?:\r\n|\r|\n)(0x[0-9a-f]+(?: 0x[0-9a-f]+)+)")
        ignore_ids = []
        start_idx = 0
        for match in re.finditer(system_re, fault):
            ignore_ids = [int(i, base=16) for i in match.group(1).split()]
            start_idx = match.span()[1]
        text = ""
        for idx, match in enumerate(re.finditer(thread_regex, fault)):
            if idx == 0:
                text += fault[start_idx:match.span()[0]]
            thread_id = int(match.group(2), base=16)
            if thread_id != main_id:
                if thread_id in ignore_ids:
                    continue
                if "wurlitzer.py" in match.group(0):
                    # Wurlitzer threads are launched later
                    continue
                text += "\n" + match.group(0) + "\n"
            else:
                try:
                    pattern = (r".*(?:/IPython/core/interactiveshell\.py|"
                               r"\\IPython\\core\\interactiveshell\.py).*")
                    match_internal = next(re.finditer(pattern, match.group(0)))
                    end_idx = match_internal.span()[0]
                except StopIteration:
                    end_idx = None
                text += "\nMain thread:\n" + match.group(0)[:end_idx] + "\n"
        return text

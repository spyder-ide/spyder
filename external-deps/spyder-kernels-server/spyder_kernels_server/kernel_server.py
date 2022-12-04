# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""Jupyter Kernels for the Spyder consoles."""

# Standard library imports
import os
import os.path as osp
from subprocess import PIPE
import uuid

from threading import Thread


# Third-party imports
from jupyter_core.paths import jupyter_runtime_dir

from spyder_kernels_server.kernel_manager import SpyderKernelManager
from spyder_kernels_server.kernel_comm import KernelComm


PERMISSION_ERROR_MSG = (
    "The directory {} is not writable and it is required to create IPython "
    "consoles. Please make it writable."
)

# kernel_comm needs a qthread
class StdThread(Thread):
    """Poll for changes in std buffers."""
    def __init__(self, std_buffer, buffer_key, kernel_comm):
        self._std_buffer = std_buffer

        self.buffer_key = buffer_key
        self.kernel_comm = kernel_comm
        super().__init__()

    def run(self):
        txt = True
        while txt:
            txt = self._std_buffer.read1()
            if txt:
                # Needs to be on control so the message is sent to currently
                # executing shell
                self.kernel_comm.remote_call(
                    interrupt=True
                ).print_remote(
                    txt.decode(),
                    self.buffer_key
                )


class ShutdownThread(Thread):
    def __init__(self, kernel_dict):
        self.kernel_dict = kernel_dict
        super().__init__()

    def run(self):
        """Shutdown kernel."""
        kernel_manager = self.kernel_dict["kernel"]

        if not kernel_manager.shutting_down:
            kernel_manager.shutting_down = True
            try:
                kernel_manager.shutdown_kernel()
            except Exception:
                # kernel was externally killed
                pass
        if "stdout" in self.kernel_dict:
            self.kernel_dict["stdout" ].join()
        if "stderr" in self.kernel_dict:
            self.kernel_dict["stderr" ].join()


class KernelServer:

    def __init__(self):
        self._kernel_list = {}

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


    def open_kernel(self, kernel_spec):
        """
        Create a new kernel.

        Might raise all kinds of exceptions
        """
        connection_file = self.new_connection_file()
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

        kernel_key = connection_file
        self._kernel_list[kernel_key] = {
            "kernel": kernel_manager
            }

        kernel_client = kernel_manager.client()
        kernel_client.start_channels()
        kernel_comm = KernelComm()
        kernel_comm.open_comm(kernel_client)
        self.connect_std_pipes(kernel_key, kernel_comm)


        return connection_file

    def connect_std_pipes(self, kernel_key, kernel_comm):
        """Connect to std pipes."""

        kernel_manager = self._kernel_list[kernel_key]["kernel"]
        stdout = kernel_manager.provisioner.process.stdout
        stderr = kernel_manager.provisioner.process.stderr

        if stdout:
            stdout_thread = StdThread(
                stdout, "stdout", kernel_comm)
            stdout_thread.start()
            self._kernel_list[kernel_key]["stdout"] = stdout_thread
        if stderr:
            stderr_thread = StdThread(
                stderr, "stderr", kernel_comm)
            stderr_thread.start()
            self._kernel_list[kernel_key]["stderr"] = stderr_thread

    def close_kernel(self, kernel_key):
        """Close kernel"""
        kernel_manager = self._kernel_list[kernel_key]["kernel"]
        kernel_manager.stop_restarter()
        shutdown_thread = ShutdownThread(self._kernel_list.pop(kernel_key))
        shutdown_thread.start()

    def shutdown(self):
        for kernel_key in self._kernel_list:
            self.close_kernel(kernel_key)

# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Spyder kernel application.
"""

# Standard library imports
import os
from threading import Thread
import time

# Third-party imports
from ipykernel.kernelapp import IPKernelApp
import psutil
from traitlets import DottedObjectName
from traitlets.log import get_logger

# Local imports
from spyder_kernels.console.kernel import SpyderKernel


class SpyderParentPoller(Thread):
    """
    Daemon thread that terminates the program immediately when the parent
    process no longer exists.

    Notes
    -----
    This is based on the ParentPollerUnix class from ipykernel.
    """

    def __init__(self, parent_pid=0):
        """Initialize the poller."""
        super().__init__()
        self.parent_pid = parent_pid
        self.daemon = True

    def run(self):
        """Run the poller."""
        while True:
            if self.parent_pid != 0 and not psutil.pid_exists(self.parent_pid):
                get_logger().warning(
                    "Parent appears to have exited, shutting down."
                )
                os._exit(1)
            time.sleep(1.0)


class SpyderKernelApp(IPKernelApp):

    outstream_class = DottedObjectName(
        'spyder_kernels.console.outstream.TTYOutStream'
    )

    kernel_class = SpyderKernel

    def init_pdb(self):
        """
        This method was added in IPykernel 5.3.1 and it replaces
        the debugger used by the kernel with a new class
        introduced in IPython 7.15 during kernel's initialization.
        Therefore, it doesn't allow us to use our debugger.
        """
        pass

    def close(self):
        """Close the loopback socket."""
        socket = self.kernel.loopback_socket
        if socket and not socket.closed:
            socket.close()
        return super().close()

    def init_poller(self):
        """User our own poller."""
        # The SPY_PARENT_PID env var must be set on the Spyder side.
        parent_pid = int(os.environ.get("SPY_PARENT_PID") or 0)
        self.poller = SpyderParentPoller(parent_pid=parent_pid)

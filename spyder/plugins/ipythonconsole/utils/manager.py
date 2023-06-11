# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Kernel Manager subclass."""

# Standard library imports
import os
import signal

# Third party imports
from jupyter_client.utils import run_sync
import psutil
from qtconsole.manager import QtKernelManager


class SpyderKernelManager(QtKernelManager):
    """
    Spyder kernels that live in a conda environment are now properly activated
    with custom activation scripts located at plugins/ipythonconsole/scripts.

    However, on windows the batch script is terminated but not the kernel it
    started so this subclass overrides the `_kill_kernel` method to properly
    kill the started kernels by using psutil.
    """

    def __init__(self, *args, **kwargs):
        self.shutting_down = False
        return QtKernelManager.__init__(self, *args, **kwargs)

    @staticmethod
    async def kill_proc_tree(pid, sig=signal.SIGTERM, include_parent=True,
                             timeout=None, on_terminate=None):
        """
        Kill a process tree (including grandchildren) with sig and return a
        (gone, still_alive) tuple.

        "on_terminate", if specified, is a callabck function which is called
        as soon as a child terminates.

        This is an new method not present in QtKernelManager.
        """
        assert pid != os.getpid()  # Won't kill myself!

        # This is necessary to avoid showing an error when restarting the
        # kernel after it failed to start in the first place.
        # Fixes spyder-ide/spyder#11872
        try:
            parent = psutil.Process(pid)
        except psutil.NoSuchProcess:
            return ([], [])

        children = parent.children(recursive=True)

        if include_parent:
            children.append(parent)

        for child_process in children:
            # This is necessary to avoid an error when restarting the kernel
            # that started a PyQt5 application in the background. It also fixes
            # a problem when some of the kernel children are not available
            # anymore, probably because they were removed by the OS before this
            # method is able to run.
            # Fixes spyder-ide/spyder#21012
            # Fixes spyder-ide/spyder#13999
            try:
                child_process.send_signal(sig)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                return ([], [])

        gone, alive = psutil.wait_procs(
            children,
            timeout=timeout,
            callback=on_terminate,
        )

        return (gone, alive)

    async def _async_kill_kernel(self, restart: bool = False) -> None:
        """Kill the running kernel.
        Override private method of jupyter_client 7 to be able to correctly
        close kernel that was started via a batch/bash script for correct conda
        env activation.
        """
        if self.has_kernel:
            assert self.provisioner is not None

            # This is the additional line that was added to properly
            # kill the kernel started by Spyder.
            await self.kill_proc_tree(self.provisioner.process.pid)

            await self.provisioner.kill(restart=restart)

            # Wait until the kernel terminates.
            import asyncio
            try:
                await asyncio.wait_for(self._async_wait(), timeout=5.0)
            except asyncio.TimeoutError:
                # Wait timed out, just log warning but continue
                #  - not much more we can do.
                self.log.warning("Wait for final termination of kernel timed"
                                 " out - continuing...")
                pass
            else:
                # Process is no longer alive, wait and clear
                if self.has_kernel:
                    await self.provisioner.wait()

    _kill_kernel = run_sync(_async_kill_kernel)

    async def _async_send_kernel_sigterm(self, restart: bool = False) -> None:
        """similar to _kill_kernel, but with sigterm (not sigkill), but do not block"""
        if self.has_kernel:
            assert self.provisioner is not None

            # This is the line that was added to properly kill kernels started
            # by Spyder.
            await self.kill_proc_tree(self.provisioner.process.pid)

    _send_kernel_sigterm = run_sync(_async_send_kernel_sigterm)

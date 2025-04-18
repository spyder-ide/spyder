"""Test QtInProcessKernel"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from qtconsole.inprocess import QtInProcessKernelManager
from inspect import iscoroutinefunction
import pytest


@pytest.mark.asyncio
async def test_execute():
    kernel_manager = QtInProcessKernelManager()
    if iscoroutinefunction(kernel_manager.start_kernel):
        await kernel_manager.start_kernel()
    else:
        kernel_manager.start_kernel()
    kernel_client = kernel_manager.client()

    """Test execution of shell commands."""
    # check that closed works as expected
    assert not kernel_client.iopub_channel.closed()

    # check that running code works
    kernel_client.execute("a=1")
    assert kernel_manager.kernel is not None, "kernel has likely not started"
    assert kernel_manager.kernel.shell.user_ns.get("a") == 1

    kernel_client.stop_channels()
    kernel_manager.shutdown_kernel()

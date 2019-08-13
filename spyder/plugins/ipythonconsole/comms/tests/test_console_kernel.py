#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug  5 16:43:33 2019

@author: quentinpeter
"""
from ipykernel.tests.test_embed_kernel import setup_kernel
from qtconsole.comms import CommManager
import pytest

from spyder.plugins.ipythonconsole.comms.kernelcomm import KernelComm
from spyder_kernels.py3compat import PY3, to_text_string


TIMEOUT = 15


def test_runcell(tmpdir):
    """Test the runcell command."""
    # Command to start the kernel
    cmd = "from spyder_kernels.console import start; start.main()"

    with setup_kernel(cmd) as client:
        # Write code with a cell to a file
        code = u"result = 10; fname = __file__"
        p = tmpdir.join("cell-test.py")
        p.write(code)

        class Signal():
            def connect(self, function):
                self.function = function

        # Fake Qt signal
        iopub_recieved = Signal()
        client.iopub_channel.message_received = iopub_recieved
        # Open comm
        comm_manager = CommManager(client)
        kernel_comm = KernelComm()
        kernel_comm._register_comm(comm_manager.new_comm('spyder_api', data={
                'pickle_protocol': 2}))

        def process_msg():
            msg = {'msg_type': None}
            while msg['msg_type'] != 'comm_msg':
                msg = client.get_iopub_msg(block=True, timeout=TIMEOUT)
                iopub_recieved.function(msg)

        def runcell(cellname, filename):
            return code

        kernel_comm.register_call_handler('run_cell', runcell)

        process_msg()

        # Execute runcell
        client.execute(u"runcell('', r'{}')".format(to_text_string(p)))
        # Get the runcell call
        process_msg()
        msg = client.get_shell_msg(block=True, timeout=TIMEOUT)

        # Verify that the `result` variable is defined
        client.inspect('result')
        msg = client.get_shell_msg(block=True, timeout=TIMEOUT)
        content = msg['content']
        assert content['found']

        # Verify that the `fname` variable is `cell-test.py`
        client.inspect('fname')
        msg = client.get_shell_msg(block=True, timeout=TIMEOUT)
        content = msg['content']
        assert "cell-test.py" in content['data']['text/plain']

        # Verify that the `__file__` variable is undefined
        client.inspect('__file__')
        msg = client.get_shell_msg(block=True, timeout=TIMEOUT)
        content = msg['content']
        assert not content['found']


if __name__ == "__main__":
    pytest.main()

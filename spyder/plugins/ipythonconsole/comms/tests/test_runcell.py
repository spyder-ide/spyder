# -*- coding: utf-8 -*-
# Copyright © 2018- Spyder Kernels Contributors
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)

from flaky import flaky
from ipykernel.tests.test_embed_kernel import setup_kernel
from qtconsole.comms import CommManager
import pytest
import time

from spyder.plugins.ipythonconsole.comms.kernelcomm import KernelComm
from spyder_kernels.py3compat import PY3, to_text_string


TIMEOUT = 15


@flaky(max_runs=3)
@pytest.mark.parametrize(
    "debug", [True, False])
def test_runcell(tmpdir, debug):
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

        def process_msg(call_name):
            msg = {'msg_type': None}
            while (msg['msg_type'] != 'comm_msg'
                   or msg['content']['data']['content']['call_name'] != call_name):
                msg = client.get_iopub_msg(block=True, timeout=TIMEOUT)
                iopub_recieved.function(msg)

        def runcell(cellname, filename):
            return code

        def set_debug_state(state):
            set_debug_state.state = state

        set_debug_state.state = None
        kernel_comm.register_call_handler('run_cell', runcell)
        kernel_comm.register_call_handler('get_breakpoints', lambda: {})
        kernel_comm.register_call_handler('pdb_state', lambda state: None)
        kernel_comm.register_call_handler('set_debug_state', set_debug_state)

        if debug:
            function = 'debugcell'
        else:
            function = 'runcell'
        # Execute runcell
        client.execute(function + u"('', r'{}')".format(to_text_string(p)))

        # Get the runcell call
        process_msg('run_cell')

        if debug:
            # Continue
            process_msg('set_debug_state')
            process_msg('get_breakpoints')
            assert set_debug_state.state
            time.sleep(.5)
            client.input('c')
            process_msg('set_debug_state')
            assert not set_debug_state.state

        msg = client.get_shell_msg(block=True, timeout=TIMEOUT)
        assert msg['msg_type'] == 'execute_reply'

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

# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © 2018- Spyder Kernels Contributors
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for the console kernel.
"""

# Standard library imports
import os

# Test imports
import pytest


# Local imports
from spyder_kernels.utils.test_utils import get_kernel
from spyder_kernels.comms.frontendcomm import FrontendComm
from spyder.plugins.ipythonconsole.comms.kernelcomm import KernelComm


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def kernel(request):
    """Console kernel fixture"""
    # Get kernel instance
    kernel = get_kernel()
    kernel.namespace_view_settings = {'check_all': False,
                                      'exclude_private': True,
                                      'exclude_uppercase': True,
                                      'exclude_capitalized': False,
                                      'exclude_unsupported': True,
                                      'excluded_names': ['nan', 'inf',
                                                         'infty',
                                                         'little_endian',
                                                         'colorbar_doc',
                                                         'typecodes',
                                                         '__builtins__',
                                                         '__main__',
                                                         '__doc__',
                                                         'NaN', 'Inf',
                                                         'Infinity',
                                                         'sctypes',
                                                         'rcParams',
                                                         'rcParamsDefault',
                                                         'sctypeNA', 'typeNA',
                                                         'False_', 'True_'],
                                      'minmax': False}

    # Teardown
    def reset_kernel():
        kernel.do_execute('reset -f', True)
    request.addfinalizer(reset_kernel)
    return kernel


class dummyComm():
    def __init__(self):
        self.other = None
        self.message_callback = None
        self.close_callback = None
        self.comm_id = 1

    def close(self):
        self.other.close_callback({'content': {'comm_id': self.comm_id}})

    def send(self, msg_dict, buffers=None):
        msg = {
            'buffers': buffers,
            'content': {'data': msg_dict, 'comm_id': self.comm_id},
            }
        self.other.message_callback(msg)

    def on_msg(self, callback):
        self.message_callback = callback

    def on_close(self, callback):
        self.close_callback = callback


@pytest.fixture
def comms(kernel):
    """Get the comms"""
    commA = dummyComm()
    commB = dummyComm()
    commA.other = commB
    commB.other = commA

    frontend_comm = FrontendComm(kernel)
    kernel_comm = KernelComm()

    class DummyKernelClient():
        comm_channel = None

    kernel_comm.kernel_client = DummyKernelClient()

    kernel_comm._register_comm(commA)

    # Bypass the target system as this is not what is being tested
    frontend_comm._comm_open(commB,
                             {'content': {'data': {'pickle_protocol': 2}}})

    return (kernel_comm, frontend_comm)


# =============================================================================
# Tests
# =============================================================================
@pytest.mark.skipif(os.name == 'nt', reason="Hangs on Windows")
def test_comm_base(comms):
    """Test basic message exchange."""
    commsend, commrecv = comms

    assert commsend.is_open()
    assert commrecv.is_open()

    received_messages = []

    def handler(msg_dict, buffer, load_exception):
        assert load_exception is None
        received_messages.append((msg_dict, buffer))

    # Register callback
    commrecv._register_message_handler('test_message', handler)

    # Send a message
    commsend._send_message('test_message', content='content', data='data')
    assert len(received_messages) == 1
    assert received_messages[0][0]['spyder_msg_type'] == 'test_message'
    assert received_messages[0][0]['content'] == 'content'
    assert received_messages[0][1] == 'data'

    # Send another message
    commsend._send_message('test_message', content='content', data='data')
    assert len(received_messages) == 2

    # Unregister callback
    commrecv._register_message_handler('test_message', None)

    # Send another unhandled message
    commsend._send_message('test_message', content='content', data='data')
    assert len(received_messages) == 2

    # Test closing
    commsend.close()
    assert not commsend.is_open()
    assert not commrecv.is_open()


@pytest.mark.skipif(os.name == 'nt', reason="Hangs on Windows")
def test_request(comms):
    """Test if the requests are being replied to."""
    kernel_comm, frontend_comm = comms

    def handler(a, b):
        return a + b

    kernel_comm.register_call_handler('test_request', handler)

    res = frontend_comm.remote_call(blocking=True).test_request('a', b='b')

    assert res == 'ab'


if __name__ == "__main__":
    pytest.main()

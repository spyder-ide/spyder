# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
In addition to the remote_call mechanism implemented in CommBase:
 - Send a message to a debugging kernel
"""
from contextlib import contextmanager
import logging
import pickle

import jupyter_client
from qtpy.QtCore import QEventLoop, QObject, QTimer, Signal
import zmq

from spyder_kernels.comms.commbase import CommBase
from spyder.py3compat import TimeoutError

logger = logging.getLogger(__name__)

# Patch jupyter_client to define 'comm' as a socket type
jupyter_client.connect.channel_socket_types['comm'] = zmq.DEALER


class KernelComm(CommBase, QObject):
    """
    Class with the necessary attributes and methods to handle
    communications with a console.
    """

    _sig_got_reply = Signal()
    sig_exception_occurred = Signal(str, bool)

    def __init__(self):
        super(KernelComm, self).__init__()
        self.comm_port = None
        self.kernel_client = None

        # Register handlers
        self.register_call_handler('_async_error', self._async_error)
        self.register_call_handler('_set_comm_port', self._set_comm_port)


    def _set_comm_port(self, port):
        """Set comm port."""
        client = self.kernel_client
        client.comm_port = port
        identity = client.session.bsession
        socket = client._create_connected_socket(
            'comm', identity=identity)
        client.comm_channel = client.shell_channel_class(
            socket, client.session, client.ioloop)

    def shutdown_comm_channel(self):
        """Shutdown the comm channel."""
        channel = self.kernel_client.comm_channel
        if channel:
            msg = self.kernel_client.session.msg('shutdown_request', {})
            channel.send(msg)
            self.kernel_client.comm_channel = None

    @contextmanager
    def comm_channel_manager(self, comm_id):
        """Use comm_channel instead of shell_channel."""
        if not self.kernel_client.comm_channel:
            yield
            return
        id_list = self.get_comm_id_list(comm_id)
        for comm_id in id_list:
            self._comms[comm_id]['comm']._send_channel = (
                self.kernel_client.comm_channel)
        try:
            yield
        finally:
            for comm_id in id_list:
                self._comms[comm_id]['comm']._send_channel = (
                    self.kernel_client.shell_channel)

    def _set_call_return_value(self, call_dict, data, is_error=False):
        """Override to use the comm_channel for all replies."""
        with self.comm_channel_manager(self.calling_comm_id):
            super(KernelComm, self)._set_call_return_value(
                call_dict, data, is_error)

    def open_comm(self, kernel_client):
        """Open comm through the kernel client."""
        self.kernel_client = kernel_client
        self.kernel_client.comm_channel = None
        self._register_comm(
            # Create new comm and send the highest protocol
            kernel_client.comm_manager.new_comm(self._comm_name, data={
                'pickle_protocol': pickle.HIGHEST_PROTOCOL}))

    def remote_call(self, interrupt=False, blocking=False, callback=None,
                    comm_id=None, timeout=None):
        """Get a handler for remote calls."""
        return super(KernelComm, self).remote_call(
            interrupt=interrupt, blocking=blocking, callback=callback,
            comm_id=comm_id, timeout=timeout)

    # ---- Private -----
    def _get_call_return_value(self, call_dict, call_data, comm_id):
        """
        Interupt the kernel if needed.
        """
        settings = call_dict['settings']
        interrupt = 'interrupt' in settings and settings['interrupt']
        if interrupt:
            with self.comm_channel_manager(comm_id):
                return super(KernelComm, self)._get_call_return_value(
                    call_dict, call_data, comm_id)
        else:
            return super(KernelComm, self)._get_call_return_value(
                call_dict, call_data, comm_id)

    def _wait_reply(self, call_id, call_name, timeout):
        """Wait for the other side reply."""
        if call_id in self._reply_inbox:
            return

        # Create event loop to wait with
        wait_loop = QEventLoop()
        self._sig_got_reply.connect(wait_loop.quit)
        wait_timeout = QTimer()
        wait_timeout.setSingleShot(True)
        wait_timeout.timeout.connect(wait_loop.quit)

        # Wait until the kernel returns the value
        wait_timeout.start(timeout * 1000)
        while len(self._reply_waitlist) > 0:
            if not wait_timeout.isActive():
                self._sig_got_reply.disconnect(wait_loop.quit)
                if call_id in self._reply_waitlist:
                    raise TimeoutError(
                        "Timeout while waiting for {}".format(
                            self._reply_waitlist))
                return
            wait_loop.exec_()

        wait_timeout.stop()
        self._sig_got_reply.disconnect(wait_loop.quit)

    def _handle_remote_call_reply(self, msg_dict, buffer, load_exception):
        """
        A blocking call received a reply.
        """
        super(KernelComm, self)._handle_remote_call_reply(
            msg_dict, buffer, load_exception)
        self._sig_got_reply.emit()

    def _async_error(self, error_wrapper):
        """
        Handle an error that was raised on the other side and sent back.
        """
        for line in error_wrapper.format_error():
            self.sig_exception_occurred.emit(line, True)

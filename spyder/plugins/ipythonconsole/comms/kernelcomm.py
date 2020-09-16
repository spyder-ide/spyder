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
    _sig_comm_port_changed = Signal()
    sig_exception_occurred = Signal(dict)

    def __init__(self):
        super(KernelComm, self).__init__()
        self.comm_port = None
        self.kernel_client = None

        # Register handlers
        self.register_call_handler('_async_error', self._async_error)
        self.register_call_handler('_set_comm_port', self._set_comm_port)

    def _set_comm_port(self, port):
        """Set comm port."""
        if port is None:
            return
        client = self.kernel_client
        if not (hasattr(client, 'comm_port') and client.comm_port == port):
            client.comm_port = port
            identity = client.session.bsession
            socket = client._create_connected_socket(
                'comm', identity=identity)
            client.comm_channel = client.shell_channel_class(
                socket, client.session, client.ioloop)
            # We emit in case we are waiting on this
            self._sig_comm_port_changed.emit()

    def shutdown_comm_channel(self):
        """Shutdown the comm channel."""
        channel = self.kernel_client.comm_channel
        if channel:
            msg = self.kernel_client.session.msg('shutdown_request', {})
            channel.send(msg)
            self.kernel_client.comm_channel = None

    def comm_channel_connected(self):
        """Check if the comm channel is connected."""
        return self.kernel_client.comm_channel is not None

    @contextmanager
    def comm_channel_manager(self, comm_id, queue_message=False):
        """Use comm_channel instead of shell_channel."""
        if queue_message:
            # Send without comm_channel
            yield
            return

        if not self.comm_channel_connected():
            # Ask again for comm config
            self.remote_call()._send_comm_config()
            timeout = 25
            self._wait(self.comm_channel_connected,
                       self._sig_comm_port_changed,
                       "Timeout while waiting for comm port.",
                       timeout)

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
    def on_incoming_call(self, call_dict):
        """A call was received"""
        if "comm_port" in call_dict:
            self._set_comm_port(call_dict["comm_port"])
        return super(KernelComm, self).on_incoming_call(call_dict)

    def _get_call_return_value(self, call_dict, call_data, comm_id):
        """
        Interupt the kernel if needed.
        """
        settings = call_dict['settings']
        blocking = 'blocking' in settings and settings['blocking']

        if not self.kernel_client.is_alive():
            if blocking:
                raise RuntimeError("Kernel is dead")
            else:
                # The user has other problems
                return

        settings = call_dict['settings']
        interrupt = 'interrupt' in settings and settings['interrupt']

        try:
            with self.comm_channel_manager(
                    comm_id, queue_message=not interrupt):
                return super(KernelComm, self)._get_call_return_value(
                    call_dict, call_data, comm_id)
        except RuntimeError:
            if blocking:
                raise
            else:
                # The user has other problems
                return

    def _wait_reply(self, call_id, call_name, timeout):
        """Wait for the other side reply."""

        def got_reply():
            return call_id in self._reply_inbox

        timeout_msg = "Timeout while waiting for {}".format(
            self._reply_waitlist)
        self._wait(got_reply, self._sig_got_reply, timeout_msg, timeout)

    def _wait(self, condition, signal, timeout_msg, timeout):
        """
        Wait until condition() is True by running an event loop.

        signal: qt signal that should interrupt the event loop.
        timeout_msg: Message to display in case of a timeout.
        timeout: time in seconds before a timeout
        """
        # Exit if condition is fulfilled or the kernel is dead.
        if condition():
            return
        if not self.kernel_client.is_alive():
            raise RuntimeError("Kernel is dead")

        # Create event loop to wait with
        wait_loop = QEventLoop()
        wait_timeout = QTimer()
        wait_timeout.setSingleShot(True)

        # Connect signals to stop kernel loop
        wait_timeout.timeout.connect(wait_loop.quit)
        self.kernel_client.hb_channel.kernel_died.connect(wait_loop.quit)
        signal.connect(wait_loop.quit)

        # Wait until the kernel returns the value
        wait_timeout.start(timeout * 1000)
        while not condition():
            if not wait_timeout.isActive():
                signal.disconnect(wait_loop.quit)
                self.kernel_client.hb_channel.kernel_died.disconnect(
                    wait_loop.quit)
                if condition():
                    return
                if not self.kernel_client.is_alive():
                    raise RuntimeError("Kernel is dead")
                raise TimeoutError(timeout_msg)
            wait_loop.exec_()

        wait_timeout.stop()
        signal.disconnect(wait_loop.quit)
        self.kernel_client.hb_channel.kernel_died.disconnect(
            wait_loop.quit)

    def _handle_remote_call_reply(self, msg_dict, buffer):
        """
        A blocking call received a reply.
        """
        super(KernelComm, self)._handle_remote_call_reply(
            msg_dict, buffer)
        self._sig_got_reply.emit()

    def _async_error(self, error_wrapper):
        """
        Handle an error that was raised on the other side and sent back.
        """
        for line in error_wrapper.format_error():
            self.sig_exception_occurred.emit(
                dict(text=line, is_traceback=True)
            )

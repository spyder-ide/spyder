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

from qtpy.QtCore import QEventLoop, QObject, QTimer, Signal

from spyder_kernels.comms.commbase import CommBase, CommsErrorWrapper

from spyder.config.base import (
    get_debug_level, running_under_pytest)

logger = logging.getLogger(__name__)
TIMEOUT_KERNEL_START = 30


class KernelComm(CommBase, QObject):
    """
    Class with the necessary attributes and methods to handle
    communications with a console.
    """

    _sig_got_reply = Signal()
    sig_exception_occurred = Signal(dict)
    sig_comm_ready = Signal()

    def __init__(self):
        super(KernelComm, self).__init__()
        self.kernel_client = None

        # Register handlers
        self.register_call_handler('_async_error', self._async_error)
        self.register_call_handler('_comm_ready', self._comm_ready)

    def is_open(self, comm_id=None):
        """
        Check to see if the comm is open and ready to communicate.
        """
        id_list = self.get_comm_id_list(comm_id)
        if len(id_list) == 0:
            return False
        return all([self._comms[cid]['status'] == 'ready' for cid in id_list])

    @contextmanager
    def comm_channel_manager(self, comm_id, queue_message=False):
        """Use control_channel instead of shell_channel."""
        if queue_message:
            # Send without control_channel
            yield
            return

        id_list = self.get_comm_id_list(comm_id)
        for comm_id in id_list:
            self._comms[comm_id]['comm']._send_channel = (
                self.kernel_client.control_channel)
        try:
            yield
        finally:
            id_list = self.get_comm_id_list(comm_id)
            for comm_id in id_list:
                self._comms[comm_id]['comm']._send_channel = (
                    self.kernel_client.shell_channel)

    def _set_call_return_value(self, call_dict, return_value, is_error=False):
        """Override to use the comm_channel for all replies."""
        with self.comm_channel_manager(self.calling_comm_id, False):
            if is_error and (get_debug_level() or running_under_pytest()):
                # Disable error muting when debugging or testing
                call_dict['settings']['display_error'] = True
            super(KernelComm, self)._set_call_return_value(
                call_dict, return_value, is_error=is_error
            )

    def remove(self, comm_id=None, only_closing=False):
        """
        Remove the comm without notifying the other side.

        Use when the other side is already down.
        """
        id_list = self.get_comm_id_list(comm_id)
        for comm_id in id_list:
            if only_closing and self._comms[comm_id]['status'] != 'closing':
                continue
            del self._comms[comm_id]

    def close(self, comm_id=None):
        """Ask kernel to close comm and send confirmation."""
        id_list = self.get_comm_id_list(comm_id)
        for comm_id in id_list:
            # Send comm_close directly to avoid really closing the comm
            self._comms[comm_id]['comm']._send_msg(
                'comm_close', {}, None, None, None)
            self._comms[comm_id]['status'] = 'closing'

    def open_comm(self, kernel_client):
        """Open comm through the kernel client."""
        self.kernel_client = kernel_client
        try:
            logger.debug(
                f"Opening kernel comm for "
                f"{'<' + repr(kernel_client).split('.')[-1]}"
            )

            self._register_comm(
                # Create new comm and send the highest protocol
                kernel_client.comm_manager.new_comm(self._comm_name)
            )
        except AttributeError:
            logger.info(
                "Unable to open comm due to unexistent comm manager: " +
                "kernel_client.comm_manager=" + str(kernel_client.comm_manager)
            )

    def remote_call(self, interrupt=False, blocking=False, callback=None,
                    comm_id=None, timeout=None, display_error=False):
        """Get a handler for remote calls."""
        return super(KernelComm, self).remote_call(
            interrupt=interrupt, blocking=blocking, callback=callback,
            comm_id=comm_id, timeout=timeout, display_error=display_error)

    def on_incoming_call(self, call_dict):
        """A call was received"""
        super().on_incoming_call(call_dict)
        # Just in case the call was not received
        self._comm_ready()

    # ---- Private -----
    def _comm_ready(self):
        """If this function is called, the comm is ready"""
        if self._comms[self.calling_comm_id]['status'] != 'ready':
            self._comms[self.calling_comm_id]['status'] = 'ready'
            self.sig_comm_ready.emit()

    def _send_call(self, call_dict, comm_id, buffers):
        """Send call and interupt the kernel if needed."""
        settings = call_dict['settings']
        blocking = 'blocking' in settings and settings['blocking']
        interrupt = 'interrupt' in settings and settings['interrupt']
        queue_message = not interrupt and not blocking

        if not self.kernel_client.is_alive():
            if blocking:
                raise RuntimeError("Kernel is dead")
            else:
                # The user has other problems
                logger.info(
                    "Dropping message because kernel is dead: %s",
                    str(call_dict)
                )
                return

        with self.comm_channel_manager(
                comm_id, queue_message=queue_message):
            return super(KernelComm, self)._send_call(
                call_dict, comm_id, buffers
            )

    def _get_call_return_value(self, call_dict, comm_id):
        """
        Catch exception if call is not blocking.
        """
        try:
            return super(KernelComm, self)._get_call_return_value(
                call_dict, comm_id)
        except RuntimeError as e:
            settings = call_dict['settings']
            blocking = 'blocking' in settings and settings['blocking']
            if blocking:
                raise
            else:
                # The user has other problems
                logger.info(
                    "Dropping message because of exception: ",
                    str(e),
                    str(call_dict)
                )
                return

    def _wait_reply(self, comm_id, call_id, call_name, timeout):
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
        wait_loop = QEventLoop(None)
        wait_timeout = QTimer(self)
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

    def _handle_remote_call_reply(self, *args, **kwargs):
        """
        A blocking call received a reply.
        """
        super(KernelComm, self)._handle_remote_call_reply(*args, **kwargs)
        self._sig_got_reply.emit()

    def _async_error(self, error_wrapper):
        """
        Handle an error that was raised on the other side and sent back.
        """
        error_wrapper = CommsErrorWrapper.from_json(error_wrapper)
        for line in error_wrapper.format_error():
            self.sig_exception_occurred.emit(
                dict(text=line, is_traceback=True)
            )

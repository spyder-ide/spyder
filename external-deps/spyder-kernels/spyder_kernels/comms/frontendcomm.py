# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
In addition to the remote_call mechanism implemented in CommBase:
 - Implements _wait_reply, so blocking calls can be made.
"""

import asyncio
import pickle
import sys
import threading
import time

from IPython.core.getipython import get_ipython
import zmq

from spyder_kernels.comms.commbase import CommBase, CommError


def frontend_request(blocking, timeout=None):
    """
    Send a request to the frontend.

    If blocking is True, The return value will be returned.
    """
    if not get_ipython().kernel.frontend_comm.is_open():
        raise CommError("Can't make a request to a closed comm")
    # Get a reply from the last frontend to have sent a message
    return get_ipython().kernel.frontend_call(
        blocking=blocking,
        broadcast=False,
        timeout=timeout)


class FrontendComm(CommBase):
    """Mixin to implement the spyder_shell_api."""

    def __init__(self, kernel):
        super(FrontendComm, self).__init__()

        # Comms
        self.kernel = kernel
        self.kernel.comm_manager.register_target(
            self._comm_name, self._comm_open)
        self.comm_lock = threading.Lock()
        self._cached_messages = {}

    def close(self, comm_id=None):
        """Close the comm and notify the other side."""
        with self.comm_lock:
            return super(FrontendComm, self).close(comm_id)

    def _send_message(self, *args, **kwargs):
        """Publish custom messages to the other side."""
        with self.comm_lock:
            return super(FrontendComm, self)._send_message(*args, **kwargs)

    def poll_one(self):
        """Receive one message from comm socket."""
        out_stream = None
        if self.kernel.shell_streams:
            # If the message handler needs to send a reply,
            # use the regular shell stream.
            out_stream = self.kernel.shell_streams[0]
        try:
            ident, msg = self.kernel.session.recv(
                self.kernel.parent.control_socket, 0)
        except zmq.error.ContextTerminated:
            return
        except Exception:
            self.kernel.log.warning("Invalid Message:", exc_info=True)
            return
        msg_type = msg['header']['msg_type']

        handler = self.kernel.control_handlers.get(msg_type, None)
        if handler is None:
            self.kernel.log.warning("Unknown message type: %r", msg_type)
            return
        try:
            asyncio.run(handler(out_stream, ident, msg))
        except Exception:
            self.kernel.log.error(
                "Exception in message handler:", exc_info=True)
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            # Flush to ensure reply is sent
            if out_stream:
                out_stream.flush(zmq.POLLOUT)

    def remote_call(self, comm_id=None, blocking=False, callback=None,
                    timeout=None):
        """Get a handler for remote calls."""
        return super(FrontendComm, self).remote_call(
            blocking=blocking,
            comm_id=comm_id,
            callback=callback,
            timeout=timeout)

    def wait_until(self, condition, timeout=None):
        """Wait until condition is met. Returns False if timeout."""
        if condition():
            return True
        t_start = time.time()
        while not condition():
            if timeout is not None and time.time() > t_start + timeout:
                return False
            if threading.current_thread() is self.kernel.parent.control_thread:
                # Wait for a reply on the comm channel.
                self.poll_one()
            else:
                # Wait 10ms for a reply
                time.sleep(0.01)
        return True

    def cache_message(self, comm_id, msg):
        """Message from a comm that might be opened later."""
        if comm_id not in self._cached_messages:
            self._cached_messages[comm_id] = []
        self._cached_messages[comm_id].append(msg)

    # --- Private --------
    def _wait_reply(self, comm_id, call_id, call_name, timeout, retry=True):
        """Wait until the frontend replies to a request."""
        def reply_received():
            """The reply is there!"""
            return call_id in self._reply_inbox
        if not self.wait_until(reply_received):
            if retry:
                self._wait_reply(comm_id, call_id, call_name, timeout, False)
                return
            raise TimeoutError(
                "Timeout while waiting for '{}' reply.".format(
                    call_name))

    def _comm_open(self, comm, msg):
        """
        A new comm is open!
        """
        self.calling_comm_id = comm.comm_id
        self._register_comm(comm)
        self._set_pickle_protocol(
            msg['content']['data']['pickle_highest_protocol'])
        self.remote_call()._set_pickle_protocol(pickle.HIGHEST_PROTOCOL)
        # Handle cached messages
        if comm.comm_id in self._cached_messages:
            for msg in self._cached_messages[comm.comm_id]:
                comm.handle_msg(msg)
            self._cached_messages.pop(comm.comm_id)


    def _comm_close(self, msg):
        """Close comm."""
        comm_id = msg['content']['comm_id']
        # Send back a close message confirmation
        # Fixes spyder-ide/spyder#15356
        self.close(comm_id)

    def _async_error(self, error_wrapper):
        """
        Send an async error back to the frontend to be displayed.
        """
        self.remote_call()._async_error(error_wrapper)

    def _register_comm(self, comm):
        """
        Remove side effect ipykernel has.
        """
        def handle_msg(msg):
            """Handle a comm_msg message"""
            if comm._msg_callback:
                comm._msg_callback(msg)
        comm.handle_msg = handle_msg
        super(FrontendComm, self)._register_comm(comm)

    def _remote_callback(self, call_name, call_args, call_kwargs):
        """Call the callback function for the remote call."""
        saved_stdout_write = sys.stdout.write
        saved_stderr_write = sys.stderr.write
        thread_id = threading.get_ident()
        sys.stdout.write = WriteWrapper(
            saved_stdout_write, call_name, thread_id)
        sys.stderr.write = WriteWrapper(
            saved_stderr_write, call_name, thread_id)
        try:
            return super(FrontendComm, self)._remote_callback(
                call_name, call_args, call_kwargs)
        finally:
            sys.stdout.write = saved_stdout_write
            sys.stderr.write = saved_stderr_write


class WriteWrapper(object):
    """Wrapper to warn user when text is printed."""

    def __init__(self, write, name, thread_id):
        self._write = write
        self._name = name
        self._thread_id = thread_id
        self._warning_shown = False

    def is_benign_message(self, message):
        """Determine if a message is benign in order to filter it."""
        benign_messages = [
            # Fixes spyder-ide/spyder#14928
            # Fixes spyder-ide/spyder-kernels#343
            'DeprecationWarning',
            # Fixes spyder-ide/spyder-kernels#365
            'IOStream.flush timed out'
        ]

        return any([msg in message for msg in benign_messages])

    def __call__(self, string):
        """Print warning once."""
        if self._thread_id != threading.get_ident():
            return self._write(string)

        if not self.is_benign_message(string):
            if not self._warning_shown:
                self._warning_shown = True

                # Don't print handler name for `show_mpl_backend_errors`
                # because we have a specific message for it.
                # request_pdb_stop is expected to print messages.
                if self._name not in [
                        'show_mpl_backend_errors', 'request_pdb_stop']:
                    self._write(
                        "\nOutput from spyder call " + repr(self._name) + ":\n"
                    )

            return self._write(string)

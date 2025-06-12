# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Class that handles communications between Spyder kernel and frontend.

Comms transmit data in a list of buffers, and in a json-able dictionnary.
Here, we only support json to avoid issues of compatibility between Python
versions. In the abstraction below, buffers is used to send bytes.

The messages exchanged have the following msg_dict:

    ```
    msg_dict = {
        'spyder_msg_type': spyder_msg_type,
        'content': content,
    }
    ```

To simplify the usage of messaging, we use a higher level function calling
mechanism:
    - The `remote_call` method returns a RemoteCallHandler object
    - By calling an attribute of this object, the call is sent to the other
      side of the comm.
    - If the `_wait_reply` is implemented, remote_call can be called with
      `blocking=True`, which will wait for a reply sent by the other side.

The messages exchanged are:
    - Function call (spyder_msg_type = 'remote_call'):
        - The content is a dictionnary {
            'call_name': The name of the function to be called,
            'call_id': uuid to match the request to a potential reply,
            'settings': A dictionnary of settings,
            'call_args': The function args,
            'call_kwargs': The function kwargs,
            'buffered_args': The args index that are in the buffers,
            'buffered_kwargs': the kwargs keys that are in the buffers
          }
        - The buffer contains any bytes in the arguments
    - If the 'settings' has `'blocking' =  True`, a reply is sent.
      (spyder_msg_type = 'remote_call_reply'):
        - The 'content' is a dict with: {
            'is_error': a boolean indicating if the return value is an
                        exception to be raised.
            'call_id': The uuid from above,
            'call_name': The function name (mostly for debugging),
            'call_return_value': The return value of the function
           }
        - The buffer contains the return value if it is bytes
"""
import logging
import sys
import uuid
import traceback
import builtins


logger = logging.getLogger(__name__)

# Max timeout (in secs) for blocking calls
TIMEOUT = 3


class CommError(RuntimeError):
    pass


def stacksummary_to_json(stack):
    """StackSummary to json."""
    return [
        {
            "filename": frame.filename,
            "lineno": frame.lineno,
            "name": frame.name,
            "line": frame.line
        }
        for frame in stack
    ]


def staksummary_from_json(stack):
    """StackSummary from json."""
    traceback.StackSummary.from_list([
        (
            frame["filename"],
            frame["lineno"],
            frame["name"],
            frame["line"]
        )
        for frame in stack
    ])


class CommsErrorWrapper():
    def __init__(self, call_name, call_id):
        self.call_name = call_name
        self.call_id = call_id
        self.etype, self.error, tb = sys.exc_info()
        self.tb = traceback.extract_tb(tb)

    def to_json(self):
        """Create JSON representation."""
        return {
            "call_name": self.call_name,
            "call_id": self.call_id,
            "etype": self.etype.__name__,
            "args": self.error.args,
            "error_name": getattr(self.error, "name", None),
            "tb": stacksummary_to_json(self.tb)
        }

    @classmethod
    def from_json(cls, json_data):
        """Get a CommsErrorWrapper from a JSON representation."""
        instance = cls.__new__(cls)
        instance.call_name = json_data["call_name"]
        instance.call_id = json_data["call_id"]
        etype = json_data["etype"]
        instance.etype = getattr(
            builtins,
            etype,
            type(etype, (Exception,), {})
        )
        instance.error = instance.etype(*json_data["args"])
        if json_data["error_name"]:
            instance.error.name = json_data["error_name"]
        instance.tb = staksummary_from_json(json_data["tb"])
        return instance

    def raise_error(self):
        """
        Raise the error while adding informations on the callback.
        """
        # Add the traceback in the error, so it can be handled upstream
        raise self.etype(self)

    def format_error(self):
        """
        Format the error received from the other side and returns a list of
        strings.
        """
        lines = (['Exception in comms call {}:\n'.format(self.call_name)]
                 + traceback.format_list(self.tb)
                 + traceback.format_exception_only(self.etype, self.error))
        return lines

    def print_error(self, file=None):
        """
        Print the error to file or to sys.stderr if file is None.
        """
        if file is None:
            file = sys.stderr
        for line in self.format_error():
            print(line, file=file)

    def __str__(self):
        """Get string representation."""
        return str(self.error)

    def __repr__(self):
        """Get repr."""
        return repr(self.error)


# Replace sys.excepthook to handle CommsErrorWrapper
sys_excepthook = sys.excepthook


def comm_excepthook(type, value, tb):
    if len(value.args) == 1 and isinstance(value.args[0], CommsErrorWrapper):
        traceback.print_tb(tb)
        value.args[0].print_error()
        return
    sys_excepthook(type, value, tb)


sys.excepthook = comm_excepthook


class CommBase:
    """
    Class with the necessary attributes and methods to handle
    communications between a kernel and a frontend.
    Subclasses must open a comm and register it with `self._register_comm`.
    """

    def __init__(self):
        super(CommBase, self).__init__()
        self.calling_comm_id = None
        self._comms = {}
        # Handlers
        self._message_handlers = {}
        self._remote_call_handlers = {}
        # Lists of reply numbers
        self._reply_inbox = {}
        self._reply_waitlist = {}

        self._register_message_handler(
            'remote_call', self._handle_remote_call)
        self._register_message_handler(
            'remote_call_reply', self._handle_remote_call_reply)

    def get_comm_id_list(self, comm_id=None):
        """Get a list of comms id."""
        if comm_id is None:
            id_list = list(self._comms.keys())
        else:
            id_list = [comm_id]
        return id_list

    def close(self, comm_id=None):
        """Close the comm and notify the other side."""
        id_list = self.get_comm_id_list(comm_id)

        for comm_id in id_list:
            try:
                self._comms[comm_id]['comm'].close()
                del self._comms[comm_id]
            except KeyError:
                pass

    def is_open(self, comm_id=None):
        """Check to see if the comm is open."""
        if comm_id is None:
            return len(self._comms) > 0
        return comm_id in self._comms

    def register_call_handler(self, call_name, handler):
        """
        Register a remote call handler.

        Parameters
        ----------
        call_name : str
            The name of the called function.
        handler : callback
            A function to handle the request.
        """
        self._remote_call_handlers[call_name] = handler

    def unregister_call_handler(self, call_name):
        """
        Unegister a remote call handler.

        Parameters
        ----------
        call_name : str
            The name of the called function.
        """
        self._remote_call_handlers.pop(call_name, None)

    def remote_call(self, comm_id=None, callback=None, **settings):
        """Get a handler for remote calls."""
        return RemoteCallFactory(self, comm_id, callback, **settings)

    # ---- Private -----
    def _send_message(
        self, spyder_msg_type, content=None, comm_id=None, buffers=None
    ):
        """
        Publish custom messages to the other side.

        Parameters
        ----------
        spyder_msg_type: str
            The spyder message type
        content: dict
            The (JSONable) content of the message
        comm_id: int
            the comm to send to. If None sends to all comms.
        buffers: list(bytes)
            a list of bytes to send.
        """
        if not self.is_open(comm_id):
            raise CommError("The comm is not connected.")
        id_list = self.get_comm_id_list(comm_id)
        for comm_id in id_list:
            msg_dict = {
                'spyder_msg_type': spyder_msg_type,
                'content': content,
            }

            self._comms[comm_id]['comm'].send(msg_dict, buffers=buffers)

    @property
    def _comm_name(self):
        """
        Get the name used for the underlying comms.
        """
        return 'spyder_api'

    def _register_message_handler(self, message_id, handler):
        """
        Register a message handler.

        Parameters
        ----------
        message_id : str
            The identifier for the message
        handler : callback
            A function to handle the message. This is called with:
                - msg_dict: A dictionary with message information.
            Pass None to unregister the message_id
        """
        if handler is None:
            self._message_handlers.pop(message_id, None)
            return

        self._message_handlers[message_id] = handler

    def _register_comm(self, comm):
        """
        Open a new comm to the kernel.
        """
        comm.on_msg(self._comm_message)
        comm.on_close(self._comm_close)
        self._comms[comm.comm_id] = {
            'comm': comm,
            'status': 'opening',
        }

    def _comm_close(self, msg):
        """Close comm."""
        comm_id = msg['content']['comm_id']
        del self._comms[comm_id]

    def _comm_message(self, msg):
        """
        Handle internal spyder messages.
        """
        self.calling_comm_id = msg['content']['comm_id']

        # Get message dict
        msg_dict = msg['content']['data']
        spyder_msg_type = msg_dict['spyder_msg_type']
        buffers = msg['buffers']

        if spyder_msg_type in self._message_handlers:
            self._message_handlers[spyder_msg_type](msg_dict, buffers)
        else:
            logger.debug("No such spyder message type: %s" % spyder_msg_type)

    def _handle_remote_call(self, msg, buffers):
        """Handle a remote call."""
        msg_dict = msg['content']
        self.on_incoming_call(msg_dict)
        try:
            # read buffers
            args = msg_dict['call_args']
            kwargs = msg_dict['call_kwargs']

            if buffers:
                for idx in msg_dict['buffered_args']:
                    args[idx] = buffers.pop(0)
                for name in msg_dict['buffered_kwargs']:
                    kwargs[name] = buffers.pop(0)
                assert len(buffers) == 0

            return_value = self._remote_callback(
                msg_dict['call_name'],
                args,
                kwargs
            )
            self._set_call_return_value(msg_dict, return_value)
        except Exception:
            exc_infos = CommsErrorWrapper(
                msg_dict['call_name'], msg_dict['call_id'])
            self._set_call_return_value(msg_dict, exc_infos, is_error=True)

    def _remote_callback(self, call_name, call_args, call_kwargs):
        """Call the callback function for the remote call."""
        if call_name in self._remote_call_handlers:
            return self._remote_call_handlers[call_name](
                *call_args, **call_kwargs)

        raise CommError("No such spyder call type: %s" % call_name)

    def _set_call_return_value(self, call_dict, return_value, is_error=False):
        """
        A remote call has just been processed.

        This will reply if settings['blocking'] == True
        """
        settings = call_dict['settings']

        display_error = ('display_error' in settings and
                         settings['display_error'])
        if is_error:
            if display_error:
                return_value.print_error()
            return_value = return_value.to_json()

        send_reply = 'send_reply' in settings and settings['send_reply']
        if not send_reply:
            # Nothing to send back
            return

        buffers = None
        if isinstance(return_value, bytes):
            buffers = [return_value]
            return_value = None

        content = {
            'is_error': is_error,
            'call_id': call_dict['call_id'],
            'call_name': call_dict['call_name'],
            'call_return_value': return_value
        }

        self._send_message(
            'remote_call_reply',
            content=content,
            comm_id=self.calling_comm_id,
            buffers=buffers
        )

    def _register_call(self, call_dict, callback=None):
        """
        Register the call so the reply can be properly treated.
        """
        settings = call_dict['settings']
        blocking = 'blocking' in settings and settings['blocking']
        call_id = call_dict['call_id']
        if blocking or callback is not None:
            self._reply_waitlist[call_id] = blocking, callback

    def on_outgoing_call(self, call_dict):
        """A message is about to be sent"""
        return call_dict

    def on_incoming_call(self, call_dict):
        """A call was received"""
        pass

    def _send_call(self, call_dict, comm_id, buffers=None):
        """Send call."""
        call_dict = self.on_outgoing_call(call_dict)
        self._send_message(
            'remote_call', content=call_dict, comm_id=comm_id, buffers=buffers
        )

    def _get_call_return_value(self, call_dict, comm_id):
        """
        Send a remote call and return the reply.

        If settings['blocking'] == True, this will wait for a reply and return
        the replied value.
        """
        settings = call_dict['settings']

        blocking = 'blocking' in settings and settings['blocking']
        if not blocking:
            return

        call_id = call_dict['call_id']
        call_name = call_dict['call_name']

        # Wait for the blocking call
        if 'timeout' in settings and settings['timeout'] is not None:
            timeout = settings['timeout']
        else:
            timeout = TIMEOUT

        self._wait_reply(comm_id, call_id, call_name, timeout)

        content = self._reply_inbox.pop(call_id)
        return_value = content['call_return_value']

        if content['is_error']:
            return self._sync_error(return_value)
        return return_value

    def _wait_reply(self, comm_id, call_id, call_name, timeout):
        """
        Wait for the other side reply.
        """
        raise NotImplementedError

    def _handle_remote_call_reply(self, msg_dict, buffers):
        """
        A blocking call received a reply.
        """
        content = msg_dict['content']
        call_id = content['call_id']
        call_name = content['call_name']
        is_error = content['is_error']
        return_value = content['call_return_value']

        # Prepare return value
        if is_error:
            return_value = CommsErrorWrapper.from_json(return_value)
        elif buffers:
            assert len(buffers) == 1
            return_value = buffers[0]
        content['call_return_value'] = return_value

        # Unexpected reply
        if call_id not in self._reply_waitlist:
            if is_error:
                return self._async_error(return_value)
            else:
                logger.debug('Got an unexpected reply {}, id:{}'.format(
                    call_name, call_id))
            return

        blocking, callback = self._reply_waitlist.pop(call_id)

        # Async error
        if is_error and not blocking:
            return self._async_error(return_value)

        # Callback
        if callback is not None and not is_error:
            callback(return_value)

        # Blocking inbox
        if blocking:
            self._reply_inbox[call_id] = content

    def _async_error(self, error_wrapper):
        """
        Handle an error that was raised on the other side asyncronously.
        """
        error_wrapper.print_error()

    def _sync_error(self, error_wrapper):
        """
        Handle an error that was raised on the other side syncronously.
        """
        error_wrapper.raise_error()


class RemoteCallFactory:
    """Class to create `RemoteCall`s."""

    def __init__(self, comms_wrapper, comm_id, callback, **settings):
        # Avoid setting attributes
        super(RemoteCallFactory, self).__setattr__(
            '_comms_wrapper', comms_wrapper)
        super(RemoteCallFactory, self).__setattr__('_comm_id', comm_id)
        super(RemoteCallFactory, self).__setattr__('_callback', callback)
        super(RemoteCallFactory, self).__setattr__('_settings', settings)

    def __getattr__(self, name):
        """Get a call for a function named 'name'."""
        return RemoteCall(name, self._comms_wrapper, self._comm_id,
                          self._callback, self._settings)

    def __setattr__(self, name, value):
        """Set an attribute to the other side."""
        raise NotImplementedError


class RemoteCall():
    """Class to call the other side of the comms like a function."""

    def __init__(self, name, comms_wrapper, comm_id, callback, settings):
        self._name = name
        self._comms_wrapper = comms_wrapper
        self._comm_id = comm_id
        self._settings = settings
        self._callback = callback

    def __call__(self, *args, **kwargs):
        """
        Transmit the call to the other side of the tunnel.

        The args and kwargs have to be JSON-serializable or bytes.
        """
        blocking = 'blocking' in self._settings and self._settings['blocking']
        self._settings['send_reply'] = blocking or self._callback is not None

        # The call will be serialized with json. The bytes are sent separately.
        buffers = []
        buffered_args = []
        buffered_kwargs = []
        args = list(args)

        for i, arg in enumerate(args):
            if isinstance(arg, bytes):
                buffers.append(arg)
                buffered_args.append(i)
                args[i] = None

        for name in kwargs:
            arg = kwargs[name]
            if isinstance(arg, bytes):
                buffers.append(arg)
                buffered_kwargs.append(name)
                kwargs[name] = None

        call_id = uuid.uuid4().hex
        call_dict = {
            'call_name': self._name,
            'call_id': call_id,
            'settings': self._settings,
            'call_args': args,
            'call_kwargs': kwargs,
            'buffered_args': buffered_args,
            'buffered_kwargs': buffered_kwargs
        }

        if not self._comms_wrapper.is_open(self._comm_id):
            # Only an error if the call is blocking.
            if blocking:
                raise CommError("The comm is not connected.")
            logger.debug("Call to unconnected comm: %s" % self._name)
            return
        self._comms_wrapper._register_call(call_dict, self._callback)
        self._comms_wrapper._send_call(call_dict, self._comm_id, buffers)
        return self._comms_wrapper._get_call_return_value(
            call_dict, self._comm_id)

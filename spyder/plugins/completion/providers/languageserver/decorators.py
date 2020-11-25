# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client auxiliar decorators."""

import functools
from spyder.plugins.completion.languageserver.transport import MessageKind


def send_request(req=None, method=None):
    """Send message as a proper JSON-RPC request."""
    if req is None:
        return functools.partial(send_request, method=method)

    return send_message(req, method, kind=MessageKind.REQUEST)


def send_notification(req=None, method=None):
    """Send message as a proper JSON-RPC notification."""
    if req is None:
        return functools.partial(send_notification, method=method)

    return send_message(req, method, kind=MessageKind.NOTIFICATION)


def send_response(req=None, method=None):
    """Send message as a proper JSON-RPC response."""
    if req is None:
        return functools.partial(send_response, method=method)

    return send_message(req, method, kind=MessageKind.RESPONSE)


def send_message(req=None, method=None, kind=MessageKind.REQUEST):
    """Call function req and then send its results via ZMQ."""
    @functools.wraps(req)
    def wrapper(self, *args, **kwargs):
        params = req(self, *args, **kwargs)
        _id = self.send(method, params, kind)
        return _id
    wrapper._sends = method
    return wrapper


def class_register(cls):
    """Class decorator that allows to map LSP method names to class methods."""
    cls.handler_registry = {}
    cls.sender_registry = {}
    for method_name in dir(cls):
        method = getattr(cls, method_name)
        if hasattr(method, '_handle'):
            cls.handler_registry.update({method._handle: method_name})
        if hasattr(method, '_sends'):
            cls.sender_registry.update({method._sends: method_name})
    return cls


def handles(method_name):
    """Assign an LSP method name to a python handler."""
    def wrapper(func):
        func._handle = method_name
        return func
    return wrapper

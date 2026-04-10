# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder Language Server Protocol Client auxiliary decorators.

send_request / send_notification / send_response are now *marker* decorators:
they tag a method with the LSP method name it corresponds to and its kind
('request', 'notification', 'response').  The actual sending is done by
LSPClient.perform_request(), which inspects these attributes via the
sender_registry built by @class_register.

Each tagged method is expected to:
  - Accept Spyder's internal params dict.
  - Return a lsprotocol typed object (the LSP params to send), or None to
    cancel the operation.

@handles(method_name) marks a method as the handler for an LSP response or
server-initiated notification carrying that method name.

@class_register scans a class at definition time and builds:
  - handler_registry  : {method_name: handler_method_name}
  - sender_registry   : {method_name: sender_method_name}
  - notification_registry : {method_name}; subset of sender methods that are
                            notifications (no response expected).
"""

import functools


def send_request(req=None, method=None):
    """Mark *req* as a method that builds params for an LSP request."""
    if req is None:
        return functools.partial(send_request, method=method)
    req._sends = method
    req._kind = 'request'
    return req


def send_notification(req=None, method=None):
    """Mark *req* as a method that builds params for an LSP notification."""
    if req is None:
        return functools.partial(send_notification, method=method)
    req._sends = method
    req._kind = 'notification'
    return req


def send_response(req=None, method=None):
    """
    Mark *req* as a handler for a server-request that requires a response.

    With pygls the response is sent automatically by the feature manager when
    the registered handler returns a value, so this decorator is retained
    only for semantic clarity and registry bookkeeping.
    """
    if req is None:
        return functools.partial(send_response, method=method)
    req._sends = method
    req._kind = 'response'
    return req


def class_register(cls):
    """
    Class decorator that builds handler and sender registries from decorated
    methods, enabling dynamic dispatch in LSPClient.
    """
    cls.handler_registry = {}
    cls.sender_registry = {}
    cls.notification_registry = set()

    for method_name in dir(cls):
        method = getattr(cls, method_name)
        if hasattr(method, '_handle'):
            cls.handler_registry[method._handle] = method_name
        if hasattr(method, '_sends'):
            cls.sender_registry[method._sends] = method_name
            if getattr(method, '_kind', 'request') in ('notification', 'response'):
                cls.notification_registry.add(method._sends)

    return cls


def handles(method_name):
    """Tag a method as the handler for LSP *method_name* responses/notifications."""
    def wrapper(func):
        func._handle = method_name
        return func
    return wrapper

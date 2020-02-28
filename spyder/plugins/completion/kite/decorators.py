# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite client dispatcher decorators."""

import functools


def send_request(req=None, method=None):
    """Call function req and then send its results via HTTP."""
    if req is None:
        return functools.partial(send_request, method=method)

    @functools.wraps(req)
    def wrapper(self, *args, **kwargs):
        url_params = {}
        params = req(self, *args, **kwargs)
        if isinstance(params, tuple):
            params, url_params = params
        response = self.send(method, params, url_params)
        return response
    wrapper._sends = method
    return wrapper


def class_register(cls):
    """Class decorator that maps Kite HTTP method names to class methods."""
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
    """Assign a Kite HTTP method name to a python handler."""
    def wrapper(func):
        func._handle = method_name
        return func
    return wrapper

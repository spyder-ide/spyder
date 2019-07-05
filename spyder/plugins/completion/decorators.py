# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder completion plugin auxiliar decorators (Sourcecode)."""

import functools


def request(req=None, method=None, requires_response=True):
    """Call function req and then emit its results to the completion server."""
    if req is None:
        return functools.partial(request, method=method,
                                 requires_response=requires_response)

    @functools.wraps(req)
    def wrapper(self, *args, **kwargs):
        params = req(self, *args, **kwargs)
        if params is not None and self.completions_available:
            self.emit_request(method, params, requires_response)
    return wrapper


def class_register(cls):
    """Class decorator that maps completion method names to class methods."""
    cls.handler_registry = {}
    for method_name in dir(cls):
        method = getattr(cls, method_name)
        if hasattr(method, '_handle'):
            cls.handler_registry.update({method._handle: method_name})
    return cls


def handles(method_name):
    """Assign an completion method name to a python handler."""
    def wrapper(func):
        func._handle = method_name
        return func
    return wrapper

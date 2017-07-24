# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client auxiliar decorators."""

import functools


def send_request(req):
    """Call function req and then send its results via ZMQ."""
    @functools.wraps(req)
    def wrapper(self, *args, **kwargs):
        method, params, requires_response = req(self, *args, **kwargs)
        self.send(method, params, requires_response)
    return wrapper


def class_register(cls):
    """Class decorator that allows to map LSP method names to class methods."""
    cls.handler_registry = {}
    for method_name in dir(cls):
        method = getattr(cls, method_name)
        if hasattr(method, '_handle'):
            cls.handler_registry.update({method._handle: method})
    return cls


def handles(method_name):
    """Assign an LSP method to a method."""
    def wrapper(func):
        func._handle = method_name
        return func
    return wrapper

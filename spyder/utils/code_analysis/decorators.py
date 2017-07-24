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

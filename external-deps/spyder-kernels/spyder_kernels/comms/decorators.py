# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Comms decorators.
"""


def comm_handler(fun):
    """Decorator to mark comm handler methods."""
    fun._is_comm_handler = True
    return fun


def register_comm_handlers(instance, frontend_comm):
    """
    Registers an instance whose methods have been marked with comm_handler.
    """
    for method_name in instance.__class__.__dict__:
        method = getattr(instance, method_name)
        if hasattr(method, '_is_comm_handler'):
            frontend_comm.register_call_handler(
                method_name, method)

def kernel_config(key):
    """Decorarot to mark function as kernel config for set_configuration."""
    def config_decorator(fun):
        fun._is_kernel_config = key
        return fun
    return kernel_config
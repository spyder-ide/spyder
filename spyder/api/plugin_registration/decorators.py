# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API plugin registration decorators.
"""

# Standard library imports
import functools
from typing import Callable, Optional
import inspect


def on_plugin_available(func: Callable = None,
                        plugin: Optional[str] = None):
    """
    Method decorator used to handle plugin availability on Spyder.

    The methods that use this decorator must have the following signature:
    `def method(self)` when observing a single plugin or
    `def method(self, plugin): ...` when observing multiple plugins or
    all plugins that were listed as dependencies.

    Parameters
    ----------
    func: Callable
        Method to decorate. Given by default when applying the decorator.
    plugin: Optional[str]
        Name of the requested plugin whose availability triggers the method.

    Returns
    -------
    func: Callable
        The same method that was given as input.
    """
    if func is None:
        return functools.partial(on_plugin_available, plugin=plugin)

    if plugin is None:
        # Use special __all identifier to signal that the function
        # observes all plugins listed as dependencies.
        plugin = '__all'

    func._plugin_listen = plugin
    return func


def on_plugin_teardown(func: Callable = None,
                       plugin: Optional[str] = None):
    """
    Method decorator used to handle plugin teardown on Spyder.

    This decorator will be called **before** the specified plugin is deleted
    and also **before** the plugin that uses the decorator is destroyed.

    The methods that use this decorator must have the following signature:
    `def method(self)`.

    Parameters
    ----------
    func: Callable
        Method to decorate. Given by default when applying the decorator.
    plugin: str
        Name of the requested plugin whose teardown triggers the method.

    Returns
    -------
    func: Callable
        The same method that was given as input.
    """
    if func is None:
        return functools.partial(on_plugin_teardown, plugin=plugin)

    if plugin is None:
        raise ValueError('on_plugin_teardown must have a well defined '
                         'plugin keyword argument value, '
                         'e.g., plugin=Plugins.Editor')

    func._plugin_teardown = plugin
    return func

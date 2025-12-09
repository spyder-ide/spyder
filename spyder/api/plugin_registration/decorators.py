# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API plugin registration decorators.
"""

from __future__ import annotations

# Standard library imports
import functools
from collections.abc import Callable


def on_plugin_available(
    func: Callable | None = None,
    plugin: str | None = None,
) -> Callable:
    """
    Method decorator to handle a plugin becoming available in Spyder.

    Methods that use this decorator must have the signature

    .. code-block:: python

        def method(self):
            ...

    when observing a single plugin, or

    .. code-block:: python

        def method(self, plugin: str):
            ...

    when observing multiple plugins or all plugins listed as dependencies.

    Parameters
    ----------
    func: Callable | None, optional
        Method to decorate, passed automatically when applying the decorator.
    plugin: str | None, optional
        Name of the requested plugin whose availability triggers ``func``.
        By default, observes all plugins listed as dependencies.

    Returns
    -------
    func: Callable
        The method passed as ``func`` with the plugin listener set up.
    """
    if func is None:
        return functools.partial(on_plugin_available, plugin=plugin)

    if plugin is None:
        # Use special __all identifier to signal that the function
        # observes all plugins listed as dependencies.
        plugin = '__all'

    func._plugin_listen = plugin
    return func


def on_plugin_teardown(
    func: Callable | None = None,
    plugin: str | None = None,
) -> Callable:
    """
    Method decorator to handle plugin teardown in Spyder.

    The decorator will be called **before** the specified ``plugin`` is deleted
    and also **before** the plugin that uses the decorator is destroyed.

    Methods that use this decorator must have the signature

    .. code-block:: python

        def method(self):
            ...

    .. important::

        A plugin name must be passed to ``plugin``. While a default of ``None``
        is accepted due to technical limitations, it will raise a
        :exc:`ValueError` at runtime.

    Parameters
    ----------
    func: Callable | None, optional
        Method to decorate, passed automatically when applying the decorator.
    plugin: str
        Name of the requested plugin whose teardown triggers ``func``.
        While ``None``, the default, is accepted for technical reasons,
        :exc:`ValueError` is raised if a plugin name is not passed.

    Returns
    -------
    func: Callable
        The method passed as ``func`` with the plugin listener set up.

    Raises
    ------
    ValueError
        If an explicit plugin name is not passed to ``plugin``.
    """
    if func is None:
        return functools.partial(on_plugin_teardown, plugin=plugin)

    if plugin is None:
        raise ValueError('on_plugin_teardown must have a well defined '
                         'plugin keyword argument value, '
                         'e.g., plugin=Plugins.Editor')

    func._plugin_teardown = plugin
    return func

# -----------------------------------------------------------------------------
# Copyright (c) 2021- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

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
    Decorate a method to be called back when a specific plugin becomes ready.

    The decorated method must be a member of a
    :class:`~spyder.api.plugins.SpyderPluginV2` subclass for the decorator
    to work as intended.

    Methods to be decorated must have the signature

    .. code-block:: python

        def method(self):
            ...

    when observing a single plugin, or

    .. code-block:: python

        def method(self, plugin: str):
            ...

    when observing all plugins listed as dependencies.

    .. caution::

        Any ``plugin``\\(s) specified must be listed under either the
        :attr:`~spyder.api.plugins.SpyderPluginV2.REQUIRES` or
        :attr:`~spyder.api.plugins.SpyderPluginV2.OPTIONAL` class constants
        of the plugin's :class:`~spyder.api.plugins.SpyderPluginV2` class.
        If not, a :exc:`~spyder.api.exceptions.SpyderAPIError` will be raised
        when the plugin class is initialized.

    Parameters
    ----------
    func: Callable | None, optional
        Method to decorate, passed automatically when applying the decorator.
    plugin: str | None, optional
        Name of the requested plugin whose availability triggers ``func``.
        If ``None`` (the default), observes all plugins listed as dependencies.
        Must be listed under the class'
        ':attr:`~spyder.api.plugins.SpyderPluginV2.REQUIRES` or
        :attr:`~spyder.api.plugins.SpyderPluginV2.OPTIONAL` class constants,
        or else a :exc:`~spyder.api.exceptions.SpyderAPIError` will be raised.

    Returns
    -------
    func: Callable
        The method passed as ``func`` with the plugin listener set up.

    Raises
    ------
    SpyderAPIError
        When initializing a plugin class with decorated methods,
        if trying to watch a ``plugin`` that is not listed in the plugin class'
        :attr:`~spyder.api.plugins.SpyderPluginV2.REQUIRES` or
        :attr:`~spyder.api.plugins.SpyderPluginV2.OPTIONAL` class constants.
    """
    if func is None:
        return functools.partial(on_plugin_available, plugin=plugin)

    if plugin is None:
        # Use special __all identifier to signal that the function
        # observes all plugins listed as dependencies.
        plugin = "__all"

    func._plugin_listen = plugin
    return func


def on_plugin_teardown(
    func: Callable | None = None,
    plugin: str | None = None,
) -> Callable:
    """
    Decorate a method to be called back when tearing down a specific plugin.

    The decorated method must be a member of a
    :class:`~spyder.api.plugins.SpyderPluginV2` subclass for the decorator
    to work as intended.

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

    .. caution::

        Any ``plugin``\\(s) specified must be listed under either the
        :attr:`~spyder.api.plugins.SpyderPluginV2.REQUIRES` or
        :attr:`~spyder.api.plugins.SpyderPluginV2.OPTIONAL` class constants
        of the plugin's :class:`~spyder.api.plugins.SpyderPluginV2` class.
        If not, a :exc:`~spyder.api.exceptions.SpyderAPIError` will be raised
        when the plugin class is initialized.

    Parameters
    ----------
    func: Callable | None, optional
        Method to decorate, passed automatically when applying the decorator.
    plugin: str
        Name of the requested plugin whose teardown triggers ``func``.
        While ``None``, the default, is accepted for technical reasons,
        :exc:`ValueError` is raised if a plugin name is not passed.
        Must be listed under the class'
        ':attr:`~spyder.api.plugins.SpyderPluginV2.REQUIRES` or
        :attr:`~spyder.api.plugins.SpyderPluginV2.OPTIONAL` class constants,
        or else a :exc:`~spyder.api.exceptions.SpyderAPIError` will be raised.

    Returns
    -------
    func: Callable
        The method passed as ``func`` with the plugin listener set up.

    Raises
    ------
    ValueError
        If an explicit plugin name is not passed to ``plugin``.
    SpyderAPIError
        When initializing a plugin class with decorated methods,
        if trying to watch a ``plugin`` that is not listed in the plugin class'
        :attr:`~spyder.api.plugins.SpyderPluginV2.REQUIRES` or
        :attr:`~spyder.api.plugins.SpyderPluginV2.OPTIONAL` class constants.
    """
    if func is None:
        return functools.partial(on_plugin_teardown, plugin=plugin)

    if plugin is None:
        raise ValueError(
            "on_plugin_teardown must have a well defined "
            "plugin keyword argument value, "
            "e.g., plugin=Plugins.Editor"
        )

    func._plugin_teardown = plugin
    return func

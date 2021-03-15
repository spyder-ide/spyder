# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API helper decorators.
"""

# Standard library imports
import functools
from typing import Callable, Type, Any, Optional, Union, List
import inspect

# Local imports
from spyder.config.types import ConfigurationKey


ConfigurationKeyList = List[ConfigurationKey]
ConfigurationKeyOrList = Union[ConfigurationKeyList, ConfigurationKey]


def on_conf_change(func: Callable = None,
                   section: Optional[str] = None,
                   option: Optional[ConfigurationKeyOrList] = None) -> Callable:
    """
    Method decorator used to handle changes on the configuration option
    `option` of the section `section`.

    The methods that use this decorator must have the following signature
    `def method(self, value)` when observing a single value or the whole
    section and `def method(self, option, value): ...` when observing
    multiple values.

    Parameters
    ----------
    func: Callable
        Method to decorate. Given by default when applying the decorator.
    section: Optional[str]
        Name of the configuration whose option is going to be observed for
        changes. If None, then the `CONF_SECTION` attribute of the class
        where the method is defined is used.
    option: Optional[ConfigurationKeyOrList]
        Name/tuple of the option to observe or a list of name/tuples if the
        method expects updates from multiple keys. If None, then all changes
        on the specified section are observed.

    Returns
    -------
    func: Callable
        The same method that was given as input.
    """
    if func is None:
        return functools.partial(
            on_conf_change, section=section, option=option)

    if option is None:
        # Use special __section identifier to signal that the function
        # observes any change on the section options.
        option = '__section'

    info = []
    if isinstance(option, list):
        info = [(section, opt) for opt in option]
    else:
        info = [(section, option)]

    func._conf_listen = info
    return func

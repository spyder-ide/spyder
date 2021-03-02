# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder configuration helping types and protocols.
"""

# Standard library imports
from typing import Any, Union, Tuple, Protocol

# A configuration option in the configuration system
ConfigurationKey = Union[str, Tuple[str, ...]]


class ConfigurationObserver(Protocol):
    """
    Stub typing class that represents a object that recieves updates on
    the values of configuration options that the object subscribed to.
    """

    def on_configuration_change(self, option: ConfigurationKey, section: str,
                                value: Any):
        """
        Handle configuration updates for the option `option` on the section
        `section`, which its new value corresponds to `value`.

        Parameters
        ----------
        option: ConfigurationKey
            Configuration option that did change.
        section: str
            Name of the section where `option` is contained.
        value: Any
            New value of the configuration option that produced the event.
        """
        ...

    def __hash__(self) -> int: ...
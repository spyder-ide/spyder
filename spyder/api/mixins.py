# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API helper mixins.
"""

# Standard library imports
from typing import Any

# Local imports
from spyder.api.decorators import configuration_observer
from spyder.config.manager import CONF
from spyder.config.types import ConfigurationKey


@configuration_observer
class SpyderConfigurationObserver:
    """
    Concrete implementation of the protocol
    :class:`spyder.config.types.ConfigurationObserver`.

    This mixin enables a class to recieve configuration updates seamlessly,
    by registering methods using the
    :function:`spyder.api.decorators.on_conf_change` decorator, which recieves
    a configuration section and option to observe.

    When a change occurs on any of the registered configuration options,
    the corresponding registered method is called with the new value.
    """

    def __init__(self):
        # Register class to listen for changes in all the registered options
        for section in self._configuration_listeners:
            observed_options = self._configuration_listeners[section]
            for option in observed_options:
                CONF.observe_configuration(self, section, option)

    def __del__(self):
        # Remove object from the configuration observer
        CONF.unobserve_configuration(self)

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
        section_recievers = self._configuration_listeners.get(section, {})
        option_recievers = section_recievers.get(option, [])
        for receiver in option_recievers:
            method = getattr(self, receiver)
            method(value)

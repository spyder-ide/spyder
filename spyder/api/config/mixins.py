# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API helper mixins.
"""

# Standard library imports
import logging
from typing import Any, Union, Optional
import warnings

# Local imports
from spyder.config.manager import CONF
from spyder.config.types import ConfigurationKey
from spyder.config.user import NoDefault


logger = logging.getLogger(__name__)

BasicTypes = Union[bool, int, str, tuple, list, dict]


class SpyderConfigurationAccessor:
    """
    Mixin used to access options stored in the Spyder configuration system.
    """

    # Name of the configuration section that's going to be
    # used to record the object's permanent data in Spyder
    # config system.
    CONF_SECTION = None

    def get_conf(self,
                 option: ConfigurationKey,
                 default: Union[NoDefault, BasicTypes] = NoDefault,
                 section: Optional[str] = None):
        """
        Get an option from the Spyder configuration system.

        Parameters
        ----------
        option: ConfigurationKey
            Name/Tuple path of the option to get its value from.
        default: Union[NoDefault, BasicTypes]
            Fallback value to return if the option is not found on the
            configuration system.
        section: str
            Section in the configuration system, e.g. `shortcuts`. If None,
            then the value of `CONF_SECTION` is used.

        Returns
        -------
        value: BasicTypes
            Value of the option in the configuration section.

        Raises
        ------
        spyder.py3compat.configparser.NoOptionError
            If the option does not exist in the configuration under the given
            section and the default value is NoDefault.
        """
        section = self.CONF_SECTION if section is None else section
        if section is None:
            raise AttributeError(
                'A SpyderConfigurationAccessor must define a `CONF_SECTION` '
                'class attribute!'
            )

        return CONF.get(section, option, default)

    def set_conf(self,
                 option: ConfigurationKey,
                 value: BasicTypes,
                 section: Optional[str] = None,
                 recursive_notification: bool = True):
        """
        Set an option in the Spyder configuration system.

        Parameters
        ----------
        option: ConfigurationKey
            Name/Tuple path of the option to set its value.
        value: BasicTypes
            Value to set on the configuration system.
        section: Optional[str]
            Section in the configuration system, e.g. `shortcuts`. If None,
            then the value of `CONF_SECTION` is used.
        recursive_notification: bool
            If True, all objects that observe all changes on the
            configuration section and objects that observe partial tuple paths
            are notified. For example if the option `opt` of section `sec`
            changes, then the observers for section `sec` are notified.
            Likewise, if the option `(a, b, c)` changes, then observers for
            `(a, b, c)`, `(a, b)` and a are notified as well.
        """
        section = self.CONF_SECTION if section is None else section
        if section is None:
            raise AttributeError(
                'A SpyderConfigurationAccessor must define a `CONF_SECTION` '
                'class attribute!'
            )
        CONF.set(section, option, value,
                 recursive_notification=recursive_notification)

    def remove_conf(self,
                    option: ConfigurationKey,
                    section: Optional[str] = None):
        """
        Remove an option in the Spyder configuration system.

        Parameters
        ----------
        option: ConfigurationKey
            Name/Tuple path of the option to remove its value.
        section: Optional[str]
            Section in the configuration system, e.g. `shortcuts`. If None,
            then the value of `CONF_SECTION` is used.
        """
        section = self.CONF_SECTION if section is None else section
        if section is None:
            raise AttributeError(
                'A SpyderConfigurationAccessor must define a `CONF_SECTION` '
                'class attribute!'
            )
        CONF.remove_option(section, option)

    def get_conf_default(self,
                         option: ConfigurationKey,
                         section: Optional[str] = None):
        """
        Get an option default value in the Spyder configuration system.

        Parameters
        ----------
        option: ConfigurationKey
            Name/Tuple path of the option to remove its value.
        section: Optional[str]
            Section in the configuration system, e.g. `shortcuts`. If None,
            then the value of `CONF_SECTION` is used.
        """
        section = self.CONF_SECTION if section is None else section
        if section is None:
            raise AttributeError(
                'A SpyderConfigurationAccessor must define a `CONF_SECTION` '
                'class attribute!'
            )
        return CONF.get_default(section, option)


class SpyderConfigurationObserver(SpyderConfigurationAccessor):
    """
    Concrete implementation of the protocol
    :class:`spyder.config.types.ConfigurationObserver`.

    This mixin enables a class to receive configuration updates seamlessly,
    by registering methods using the
    :function:`spyder.api.config.decorators.on_conf_change` decorator, which
    receives a configuration section and option to observe.

    When a change occurs on any of the registered configuration options,
    the corresponding registered method is called with the new value.
    """

    def __init__(self):
        if self.CONF_SECTION is None:
            warnings.warn(
                'A SpyderConfigurationObserver must define a `CONF_SECTION` '
                f'class attribute! Hint: {self} or its parent should define '
                'the section.'
            )

        self._configuration_listeners = {}
        self._multi_option_listeners = set({})
        self._gather_observers()
        self._merge_none_observers()

        # Register class to listen for changes in all registered options
        for section in self._configuration_listeners:
            section = self.CONF_SECTION if section is None else section
            observed_options = self._configuration_listeners[section]
            for option in observed_options:
                logger.debug(f'{self} is observing {option} '
                             f'in section {section}')
                CONF.observe_configuration(self, section, option)

    def __del__(self):
        # Remove object from the configuration observer
        CONF.unobserve_configuration(self)

    def _gather_observers(self):
        """Gather all the methods decorated with `on_conf_change`."""
        for method_name in dir(self):
            method = getattr(self, method_name, None)
            if hasattr(method, '_conf_listen'):
                info = method._conf_listen
                if len(info) > 1:
                    self._multi_option_listeners |= {method_name}

                for section, option in info:
                    section_listeners = self._configuration_listeners.get(
                        section, {})
                    option_listeners = section_listeners.get(option, [])
                    option_listeners.append(method_name)
                    section_listeners[option] = option_listeners
                    self._configuration_listeners[section] = section_listeners

    def _merge_none_observers(self):
        """Replace observers that declared section as None by CONF_SECTION."""
        default_selectors = self._configuration_listeners.get(None, {})
        section_selectors = self._configuration_listeners.get(
            self.CONF_SECTION, {})

        for option in default_selectors:
            default_option_receivers = default_selectors.get(option, [])
            section_option_receivers = section_selectors.get(option, [])
            merged_receivers = (
                default_option_receivers + section_option_receivers)
            section_selectors[option] = merged_receivers

        self._configuration_listeners[self.CONF_SECTION] = section_selectors
        self._configuration_listeners.pop(None, None)

    def on_configuration_change(self, option: ConfigurationKey, section: str,
                                value: Any):
        """
        Handle configuration updates for the option `option` on the section
        `section`, whose new value corresponds to `value`.

        Parameters
        ----------
        option: ConfigurationKey
            Configuration option that did change.
        section: str
            Name of the section where `option` is contained.
        value: Any
            New value of the configuration option that produced the event.
        """
        section_receivers = self._configuration_listeners.get(section, {})
        option_receivers = section_receivers.get(option, [])
        for receiver in option_receivers:
            method = getattr(self, receiver)
            if receiver in self._multi_option_listeners:
                method(option, value)
            else:
                method(value)

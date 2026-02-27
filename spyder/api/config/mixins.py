# -----------------------------------------------------------------------------
# Copyright (c) 2021- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
Spyder API configuration helper mixins.
"""

from __future__ import annotations

# Standard library imports
import logging
import sys
import warnings
from collections.abc import Callable
from typing import Union

if sys.version_info < (3, 10):
    from typing_extensions import TypeAlias
else:
    from typing import TypeAlias  # noqa: ICN003

# Third-party imports
from qtpy import PYSIDE6

# Local imports
from spyder.config.manager import CONF, CONF_VERSION
from spyder.config.types import ConfigurationKey
from spyder.config.user import NoDefault


logger = logging.getLogger(__name__)

BasicTypes: TypeAlias = Union[bool, int, str, tuple, list, dict]
"""Type alias for the set of basic Python types supported as config values."""


class SpyderConfigurationAccessor:
    """Mixin to access options stored in the Spyder configuration system."""

    CONF_SECTION: str | None = None
    """Name of the default configuration section to use for this object.

    Will be used to record its permanent data in Spyder's config system.
    """

    def get_conf(
        self,
        option: ConfigurationKey,
        default: NoDefault | BasicTypes = NoDefault,
        section: str | None = None,
        secure: bool = False,
    ) -> BasicTypes:
        """
        Retrieve an option's value from the Spyder configuration system.

        Parameters
        ----------
        option: spyder.config.types.ConfigurationKey
            Name/tuple path of the configuration option value to get.
        default: spyder.config.user.NoDefault | BasicTypes, optional
            Fallback value to return if the option is not found on the
            configuration system. No default value if not passed.
        section: str | None, optional
            Name of the configuration section to use, e.g. ``"shortcuts"``.
            If ``None``, then the value of :attr:`CONF_SECTION` is used.
        secure: bool, optional
            If ``True``, the option will be retrieved from secure storage
            using the :mod:`!keyring` Python package. Otherwise, will be
            retrieved from Spyder's normal configuration (the default).

        Returns
        -------
        value: BasicTypes
            Value of ``option`` in the configuration ``section``.

        Raises
        ------
        configparser.NoOptionError
            If the ``section`` does not exist in Spyder's configuration.
        """
        section = self.CONF_SECTION if section is None else section
        if section is None:
            raise AttributeError(
                "A SpyderConfigurationAccessor must define a `CONF_SECTION` "
                "class attribute!"
            )

        return CONF.get(section, option, default, secure)

    def get_conf_options(self, section: str | None = None) -> list[str]:
        """
        Get all option names from the given section.

        Parameters
        ----------
        section: str | None, optional
            Name of the configuration section to use, e.g. ``"shortcuts"``.
            If ``None``, then the value of :attr:`CONF_SECTION` is used.

        Returns
        -------
        values: list[str]
            List of option names (keys) in the configuration ``section``.

        Raises
        ------
        configparser.NoOptionError
            If ``section`` does not exist in the configuration.
        """
        section = self.CONF_SECTION if section is None else section
        if section is None:
            raise AttributeError(
                "A SpyderConfigurationAccessor must define a `CONF_SECTION` "
                "class attribute!"
            )
        return CONF.options(section)

    def set_conf(
        self,
        option: ConfigurationKey,
        value: BasicTypes,
        section: str | None = None,
        recursive_notification: bool = True,
        secure: bool = False,
    ) -> None:
        """
        Set an option's value in the Spyder configuration system.

        Parameters
        ----------
        option: spyder.config.types.ConfigurationKey
            Name/tuple path of the configuration option to set.
        value: BasicTypes
            Value to set for the given configuration option.
        section: str | None, optional
            Name of the configuration section to use, e.g. ``"shortcuts"``.
            If ``None``, then the value of :attr:`CONF_SECTION` is used.
        recursive_notification: bool, optional
            If ``True``, all objects that observe all changes on the
            configuration ``section`` as well as objects that observe
            partial tuple paths are notified. For example, if the
            ``option`` ``"opt"`` of ``section`` ``"sec"`` changes, then
            all observers for section ``sec`` are notified. Likewise,
            if the option ``("a", "b", "c")`` changes, then observers for
            ``("a", "b", "c")``, ``("a", "b")`` and ``"a"`` are all notified.
        secure: bool, optional
            If ``True``, the option will be saved in secure storage
            using the :mod:`!keyring` Python package. Otherwise, will be
            saved in Spyder's normal configuration (the default).

        Returns
        -------
        None
        """
        section = self.CONF_SECTION if section is None else section
        if section is None:
            raise AttributeError(
                "A SpyderConfigurationAccessor must define a `CONF_SECTION` "
                "class attribute!"
            )
        CONF.set(
            section,
            option,
            value,
            recursive_notification=recursive_notification,
            secure=secure,
        )

    def remove_conf(
        self,
        option: ConfigurationKey,
        section: str | None = None,
        secure: bool = False,
    ) -> None:
        """
        Remove an option from the Spyder configuration system.

        Parameters
        ----------
        option: spyder.config.types.ConfigurationKey
            Name/tuple path of the configuration option to remove.
        section: str | None, optional
            Name of the configuration section to use, e.g. ``"shortcuts"``.
            If ``None``, then the value of :attr:`CONF_SECTION` is used.
        secure: bool, optional
            If ``True``, the option will be removed from secure storage
            using the :mod:`!keyring` Python package. Otherwise, will be
            removed from Spyder's normal configuration (the default).

        Returns
        -------
        None
        """
        section = self.CONF_SECTION if section is None else section
        if section is None:
            raise AttributeError(
                "A SpyderConfigurationAccessor must define a `CONF_SECTION` "
                "class attribute!"
            )
        CONF.remove_option(section, option, secure)

    def get_conf_default(
        self,
        option: ConfigurationKey,
        section: str | None = None,
    ) -> Union[NoDefault, BasicTypes]:
        """
        Get an option's default value from the Spyder configuration system.

        Parameters
        ----------
        option: spyder.config.types.ConfigurationKey
            Name/tuple path of the config option to get the default value of.
        section: str | None, optional
            Name of the configuration section to use, e.g. ``"shortcuts"``.
            If ``None``, then the value of :attr:`CONF_SECTION` is used.

        Returns
        -------
        spyder.config.user.NoDefault | BasicTypes
            The ``option``'s default value, or
            :class:`spyder.config.user.NoDefault` if one is not set.
        """
        section = self.CONF_SECTION if section is None else section
        if section is None:
            raise AttributeError(
                "A SpyderConfigurationAccessor must define a `CONF_SECTION` "
                "class attribute!"
            )
        return CONF.get_default(section, option)

    @property
    def spyder_conf_version(self) -> str:
        """Get current version of the Spyder configuration system.

        Returns
        -------
        str
            The current Spyder :const:`spyder.config.manager.CONF_VERSION`,
            as a string of ``MAJOR.MINOR.MICRO``.
        """
        return CONF_VERSION

    @property
    def old_spyder_conf_version(self) -> str:
        """Get previous version of the Spyder configuration system.

        Returns
        -------
        str
            The previous Spyder :const:`spyder.config.manager.CONF_VERSION`
            prior to the most recent Spyder update, as a string of
            ``MAJOR.MINOR.MICRO``.
        """
        return CONF.old_spyder_version


class SpyderConfigurationObserver(SpyderConfigurationAccessor):
    """
    Methods to receive and respond to changes in Spyder's configuration.

    This mixin enables a class to receive configuration updates seamlessly,
    by registering methods using the
    :func:`~spyder.api.config.decorators.on_conf_change` decorator,
    which takes a configuration section and option to observe.

    When a change occurs on any of the registered configuration options,
    the corresponding registered method is called with the new config value.
    """

    def __init__(self) -> None:
        """Create a new :class:`!SpyderConfigurationObserver`.

        .. important::

            Classes or their parents implementing this mixin must define
            a :attr:`~SpyderConfigurationAccessor.CONF_SECTION` class attribute
            with the name of their default configuration section.

        Returns
        -------
        None
        """
        super().__init__()
        if self.CONF_SECTION is None:
            warnings.warn(
                "A SpyderConfigurationObserver must define a `CONF_SECTION` "
                f"class attribute! Hint: {self} or its parent should define "
                "the section."
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
                # Avoid a crash at startup due to MRO
                if not PYSIDE6:
                    logger.debug(
                        f'{self} is observing option "{option}" in section '
                        f'"{section}"'
                    )

                CONF.observe_configuration(self, section, option)

    def __del__(self) -> None:
        """Remove an object from the configuration observer."""
        CONF.unobserve_configuration(self)

    def _gather_observers(self):
        """Gather all the methods decorated with :func:`on_conf_change`."""
        for method_name in dir(self):
            # Avoid crash at startup due to MRO
            if PYSIDE6 and method_name in {
                # PySide seems to require that the class is instantiated to
                # access this method
                "painters",
                # Method is debounced
                "restart_kernel",
            }:
                continue

            method = getattr(self, method_name, None)
            if hasattr(method, "_conf_listen"):
                info = method._conf_listen
                if len(info) > 1:
                    self._multi_option_listeners |= {method_name}

                for section, option in info:
                    self._add_listener(method_name, option, section)

    def _merge_none_observers(self):
        """Replace section ``None`` with ``CONF_SECTION`` in observers."""
        default_selectors = self._configuration_listeners.get(None, {})
        section_selectors = self._configuration_listeners.get(
            self.CONF_SECTION, {}
        )

        for option in default_selectors:
            default_option_receivers = default_selectors.get(option, [])
            section_option_receivers = section_selectors.get(option, [])
            merged_receivers = (
                default_option_receivers + section_option_receivers
            )
            section_selectors[option] = merged_receivers

        self._configuration_listeners[self.CONF_SECTION] = section_selectors
        self._configuration_listeners.pop(None, None)

    def _add_listener(
        self, func: Callable, option: ConfigurationKey, section: str
    ):
        """
        Add a callable as a listener of a specific configuration option.

        Parameters
        ----------
        func: Callable
            Function/method that will be called when ``option`` changes.
        option: spyder.config.types.ConfigurationKey
            Name/tuple path of the configuration option to observe.
        section: str
            Name of the section containing ``option``, e.g. ``"shortcuts"``.

        Returns
        -------
        None
        """
        section_listeners = self._configuration_listeners.get(section, {})
        option_listeners = section_listeners.get(option, [])
        option_listeners.append(func)
        section_listeners[option] = option_listeners
        self._configuration_listeners[section] = section_listeners

    def on_configuration_change(
        self, option: ConfigurationKey, section: str, value: BasicTypes
    ) -> None:
        """
        Handle configuration value updates for a config option.

        Parameters
        ----------
        option: spyder.config.types.ConfigurationKey
            Name/tuple path of the configuration option that changed.
        section: str
            Name of the section containing ``option``, e.g. ``"shortcuts"``.
        value: BasicTypes
            New value of the configuration option that produced the event.

        Returns
        -------
        None
        """
        section_receivers = self._configuration_listeners.get(section, {})
        option_receivers = section_receivers.get(option, [])
        for receiver in option_receivers:
            method = (
                receiver if callable(receiver) else getattr(self, receiver)
            )
            if receiver in self._multi_option_listeners:
                method(option, value)
            else:
                method(value)

    def add_configuration_observer(
        self,
        func: Callable,
        option: ConfigurationKey,
        section: str | None = None,
    ) -> None:
        """
        Add a callable to observe changes to a specific configuration option.

        Parameters
        ----------
        func: Callable
            Function/method that will be called when ``option`` changes.
        option: spyder.config.types.ConfigurationKey
            Name/tuple path of the configuration option to observe.
        section: str | None, optional
            Name of the section containing ``option``, e.g. ``"shortcuts"``.
            If ``None``, then the value of
            :attr:`~SpyderConfigurationAccessor.CONF_SECTION` is used.

        Returns
        -------
        None

        Notes
        -----
        - This is only necessary if you need to add a callable that is not a
          class method to observe an option. Otherwise, you only need to
          decorate your method with
          :func:`~spyder.api.config.decorators.on_conf_change`.
        """
        if section is None:
            section = self.CONF_SECTION

        logger.debug(
            f'{self} is observing "{option}" option on section "{section}"'
        )
        self._add_listener(func, option, section)
        CONF.observe_configuration(self, section, option)

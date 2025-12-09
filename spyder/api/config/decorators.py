# -----------------------------------------------------------------------------
# Copyright (c) 2021- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
Spyder API helper decorators.
"""

from __future__ import annotations

# Standard library imports
import functools
import sys
from collections.abc import Callable
from typing import Union

if sys.version_info < (3, 10):
    from typing_extensions import TypeAlias
else:
    from typing import TypeAlias  # noqa: ICN003

# Local imports
from spyder.config.types import ConfigurationKey


ConfigurationKeyList: TypeAlias = list[ConfigurationKey]
"""Type alias for a list of string/string tuple keys of Spyder config options.

A :class:`list` of :class:`spyder.config.types.ConfigurationKey`\\s.
"""

ConfigurationKeyOrList: TypeAlias = Union[
    ConfigurationKeyList, ConfigurationKey
]
"""Type alias for either a list of config keys or a single key.

Union of types :class:`ConfigurationKeyList` and
:class:`spyder.config.types.ConfigurationKey`.
"""


def on_conf_change(
    func: Callable | None = None,
    section: str | None = None,
    option: ConfigurationKeyOrList | None = None,
) -> Callable:
    """
    Decorator to handle changing a config option in a given section.

    The methods that use this decorator must have the signature

    .. code-block:: python

        def method(self, value: Any):
            ...

    when observing a single value or the whole section, and

    .. code-block:: python

        def method(self, option: ConfigurationKeyOrList | None, value: Any):
            ...

    when observing multiple values.

    Parameters
    ----------
    func: Callable | None, optional
        Method to decorate, passed automatically when applying the decorator.
    section: str | None, optional
        Name of the configuration section to observe for changes.
        If ``None``, then the ``CONF_SECTION`` attribute of the class
        where the method defined is used.
    option: ConfigurationKeyOrList | None, optional
        Name (:class:`str` / :class:`tuple` of :class:`str`) of the option
        to observe, or a list of names if the method expects updates from
        multiple keys. If ``None``, then all changes to options in the
        specified section are observed.

    Returns
    -------
    func: Callable
        The method passed as ``func`` with the config listener set up.
    """
    if func is None:
        return functools.partial(
            on_conf_change, section=section, option=option
        )

    if option is None:
        # Use special __section identifier to signal that the function
        # observes any change on the section options.
        option = "__section"

    info = []
    if isinstance(option, list):
        info = [(section, opt) for opt in option]
    else:
        info = [(section, option)]

    func._conf_listen = info
    return func

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API helper mixins.
"""

# Local imports
from spyder.api.decorators import configuration_observer


@configuration_observer
class SpyderConfigurationObserver:
    """
    Concrete implementation of the protocol
    :class:`spyder.config.types.ConfigurationObserver`.

    This mixin enables a class to recieve configuration updates seamlessly,
    by registering methods using the
    :function:`spyder.api.decorators.on_conf_change` decorator, which recieves
    a configuration section and option to observe.

    When a change occurs on any of the registered
    """
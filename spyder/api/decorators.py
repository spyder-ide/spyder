# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder API helper decorators.
"""


def configuration_observer(cls):
    """
    Enable a class to recieve configuration update notifications.

    This class decorator maps completion listener configuration sections and
    options to their corresponding class methods.
    """
    cls._configuration_listeners = {}
    for method_name in dir(cls):
        method = getattr(cls, method_name)
        if hasattr(method, '_conf_listen'):
            section, option = method._conf_listen
            sect_ion_listeners = cls.configuration_listeners.get(section, {})
            option_listeners = section_listeners.get(option, [])
            option_listeners.append(method_name)
            section_listeners[option] = option_listeners
            cls._configuration_listeners[section] = section_listeners
    return cls


def on_conf_change(section=None, option=None):
    """
    Method decorator used to handle changes on the configuration option
    `option` of the section `section`.

    The methods that use this decorator must have the following signature
    `def method(value): ...`
    """
    if option is None:
        option = '__section'

    def wrapper(func):
        func._conf_listen = (section, option)
        return func
    return wrapper

# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# ----------------------------------------------------------------------------

""""""

import os.path as osp

from spyder.config.base import get_home_dir, SUBFOLDER
from spyder.config.main import CONF_VERSION, DEFAULTS
from spyder.config.user import UserConfig


class ConfigurationManager:
    """"""
    _USER_CONFIG_LOCATION = None
    _SYSTEM_CONFIG_LOCATION = None

    def __init__(self):
        """"""
        self._parent = parent
        self._site_config = None
        self._project_config = None
        self._global_config = None
        self._project_configs = {}  # Cache project configurations

        self.load_config()
        self._remove_old_spyder_config_location()

    def load_config(self):
        # Main configuration instance
        try:
            self._global_config = UserConfig(
                'spyder',
                defaults=DEFAULTS,
                load=True,
                version=CONF_VERSION,
                subfolder=SUBFOLDER,
                backup=True,
                raw_mode=True)
        except Exception:
            self._global_config = UserConfig(
                'spyder',
                defaults=DEFAULTS,
                load=False,
                version=CONF_VERSION,
                subfolder=SUBFOLDER,
                backup=True,
                raw_mode=True)

    def _remove_old_spyder_config_location(self):
        """Removing old .spyder.ini location."""
        old_location = osp.join(get_home_dir(), '.spyder.ini')
        if osp.isfile(old_location):
            os.remove(old_location)

    def get(self, *args, **kwargs):
        """"""
        # TODO: User project or site config as needed
        return self._global_config.get(*args, **kwargs)

    def set(self, *args, **kwargs):
        """"""
        # TODO: User project or site config as needed
        self._global_config.set(*args, **kwargs)


CONF = ConfigurationManager()

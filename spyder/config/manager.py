# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Configuration manager providing access to user/site/project configuration.
"""

# Standard library imports
import os
import os.path as osp

# Local imports
from spyder.config.base import get_conf_path, get_home_dir
from spyder.config.main import CONF_VERSION, DEFAULTS, NAME_MAP
from spyder.config.user import MultiUserConfig, NoDefault


class ConfigurationManager(object):
    """
    Configuration manager to provide access to user/site/project config.
    """

    def __init__(self, parent=None, active_project_callback=None):
        """
        Configuration manager to provide access to user/site/project config.
        """
        path = self.get_user_config_path()
        if not osp.isdir(path):
            os.makedirs(path)

        self._parent = parent
        self._active_project_callback = active_project_callback
        self._user_config = MultiUserConfig(
            NAME_MAP,
            path=path,
            defaults=DEFAULTS,
            load=True,
            version=CONF_VERSION,
            backup=True,
            raw_mode=True,
            remove_obsolete=False,
        )
        # TODO: Implementation to be defined in following PR
        self._site_config = None

        # TODO: To be implemented in following PR
        self._project_configs = {}  # Cache project configurations

        # Setup
        self.remove_deprecated_config_locations()

    def remove_deprecated_config_locations(self):
        """Removing old .spyder.ini location."""
        old_location = osp.join(get_home_dir(), '.spyder.ini')
        if osp.isfile(old_location):
            os.remove(old_location)

    def get_system_config_path(self):
        """Return the system configuration path."""
        return None

    def get_active_conf(self):
        """
        Return the active project configuration or the user configurarion.
        """
        # TODO: implement project configuration on the following PR
        return self._user_config

    def get_user_config_path(self):
        """Return the user configuration path."""
        base_path = get_conf_path()
        path = osp.join(base_path, 'config')
        if not osp.isdir(path):
            os.makedirs(path)

        return path

    # --- Projects
    # ------------------------------------------------------------------------
    def register_config(self, root_path, config):
        """
        Register configuration with `root_path`.

        Useful for registering project configurations as they are opened.
        """
        if self.is_project_root(root_path):
            if root_path not in self._project_configs:
                self._project_configs[root_path] = config
        else:
            # Validate which are valid site config locations
            self._site_config = config

    def get_active_project(self):
        """Return the `root_path` of the current active project."""
        callback = self._active_project_callback
        if self._active_project_callback:
            return callback()

    def is_project_root(self, root_path):
        """Check if `root_path` corresponds to a valid spyder project."""
        return False

    def get_project_config_path(self, project_root):
        """Return the project configuration path."""
        path = osp.join(project_root, '.spyproj', 'config')
        if not osp.isdir(path):
            os.makedirs(path)

    # MultiUserConf/UserConf interface
    # ------------------------------------------------------------------------
    def items(self, section):
        """Return all the items option/values for the given section."""
        config = self.get_active_conf()
        return config.items(section)

    def options(self, section):
        """Return all the options for the given section."""
        config = self.get_active_conf()
        return config.options(section)

    def get(self, section, option, default=NoDefault):
        """
        Get an `option` on a given `section`.

        If section is None, the `option` is requested from default section.
        """
        config = self.get_active_conf()
        return config.get(section=section, option=option, default=default)

    def set(self, section, option, value, verbose=False, save=True):
        """
        Set an `option` on a given `section`.

        If section is None, the `option` is added to the default section.
        """
        config = self.get_active_conf()
        config.set(section=section, option=option, value=value,
                   verbose=verbose, save=save)

    def get_default(self, section, option):
        """
        Get Default value for a given `section` and `option`.

        This is useful for type checking in `get` method.
        """
        config = self.get_active_conf()
        return config.get_default(section, option)

    def remove_section(self, section):
        """Remove `section` and all options within it."""
        config = self.get_active_conf()
        config.remove_section(section)

    def remove_option(self, section, option):
        """Remove `option` from `section`."""
        config = self.get_active_conf()
        config.remove_option(section, option)

    def reset_to_defaults(self):
        """Reset config to Default values."""
        config = self.get_active_conf()
        config.reset_to_defaults()


CONF = ConfigurationManager()

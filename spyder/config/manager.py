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
from spyder.config.base import get_conf_paths, get_conf_path, get_home_dir
from spyder.config.main import CONF_VERSION, DEFAULTS, NAME_MAP
from spyder.config.user import UserConfig, MultiUserConfig, NoDefault


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

        # Site configuration defines the system defaults if a file
        # is found in the site location
        conf_paths = get_conf_paths()
        site_defaults = DEFAULTS
        for conf_path in reversed(conf_paths):
            conf_fpath = os.path.join(conf_path, 'spyder.ini')
            if os.path.isfile(conf_fpath):
                site_config = UserConfig(
                    'spyder',
                    path=conf_path,
                    defaults=site_defaults,
                    load=False,
                    version=CONF_VERSION,
                    backup=False,
                    raw_mode=True,
                    remove_obsolete=False,
                )
                site_defaults = site_config.to_list()

        self._parent = parent
        self._active_project_callback = active_project_callback
        self._user_config = MultiUserConfig(
            NAME_MAP,
            path=path,
            defaults=site_defaults,
            load=True,
            version=CONF_VERSION,
            backup=True,
            raw_mode=True,
            remove_obsolete=False,
        )

        # Store plugin configurations when CONF_FILE = True
        self._plugin_configs = {}

        # TODO: To be implemented in following PR
        self._project_configs = {}  # Cache project configurations

        # Setup
        self.remove_deprecated_config_locations()

    def register_plugin(self, plugin_class):
        """Register plugin configuration."""
        conf_section = plugin_class.CONF_SECTION
        if plugin_class.CONF_FILE and conf_section:
            path = self.get_plugin_config_path(conf_section)
            version = plugin_class.CONF_VERSION
            version = version if version else '0.0.0'
            name_map = plugin_class._CONF_NAME_MAP
            name_map = name_map if name_map else {'spyder': []}
            defaults = plugin_class.CONF_DEFAULTS

            if conf_section in self._plugin_configs:
                raise RuntimeError('A plugin with section "{}" already '
                                   'exists!'.format(conf_section))

            plugin_config = MultiUserConfig(
                name_map,
                path=path,
                defaults=defaults,
                load=True,
                version=version,
                backup=True,
                raw_mode=True,
                remove_obsolete=False,
            )
            self._plugin_configs[conf_section] = plugin_config

    def remove_deprecated_config_locations(self):
        """Removing old .spyder.ini location."""
        old_location = osp.join(get_home_dir(), '.spyder.ini')
        if osp.isfile(old_location):
            os.remove(old_location)

    def get_active_conf(self, section=None):
        """
        Return the active user or project configurarion for plugin.
        """
        if section is None:
            config = self._user_config
        elif section in self._plugin_configs:
            config = self._plugin_configs[section]
        else:
            # TODO: implement project configuration on the following PR
            config = self._user_config

        return config

    def get_user_config_path(self):
        """Return the user configuration path."""
        base_path = get_conf_path()
        path = osp.join(base_path, 'config')
        if not osp.isdir(path):
            os.makedirs(path)

        return path

    def get_plugin_config_path(self, plugin_folder):
        """Return the plugin configuration path."""
        base_path = get_conf_path()
        path = osp.join(base_path, 'plugins')
        if plugin_folder is None:
            raise RuntimeError('Plugin needs to define `CONF_SECTION`!')
        path = osp.join(base_path, 'plugins', plugin_folder)
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
        config = self.get_active_conf(section)
        return config.items(section)

    def options(self, section):
        """Return all the options for the given section."""
        config = self.get_active_conf(section)
        return config.options(section)

    def get(self, section, option, default=NoDefault):
        """
        Get an `option` on a given `section`.

        If section is None, the `option` is requested from default section.
        """
        config = self.get_active_conf(section)
        return config.get(section=section, option=option, default=default)

    def set(self, section, option, value, verbose=False, save=True):
        """
        Set an `option` on a given `section`.

        If section is None, the `option` is added to the default section.
        """
        config = self.get_active_conf(section)
        config.set(section=section, option=option, value=value,
                   verbose=verbose, save=save)

    def get_default(self, section, option):
        """
        Get Default value for a given `section` and `option`.

        This is useful for type checking in `get` method.
        """
        config = self.get_active_conf(section)
        return config.get_default(section, option)

    def remove_section(self, section):
        """Remove `section` and all options within it."""
        config = self.get_active_conf(section)
        config.remove_section(section)

    def remove_option(self, section, option):
        """Remove `option` from `section`."""
        config = self.get_active_conf(section)
        config.remove_option(section, option)

    def reset_to_defaults(self, section=None):
        """Reset config to Default values."""
        config = self.get_active_conf(section)
        config.reset_to_defaults(section=section)


CONF = ConfigurationManager()

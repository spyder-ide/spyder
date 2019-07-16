# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# ----------------------------------------------------------------------------

""""""

# Standard library imports
import copy
import os
import os.path as osp

# Local imports
from spyder.config.user import NoDefault, UserConfig
from spyder.config.base import get_conf_subfolder, get_conf_path
from spyder.config.main import CONF_VERSION, DEFAULTS


class ConfigurationManager(object):
    """"""

    def __init__(self, parent=None):
        """"""
        path = self.get_user_config_path()
        if not osp.isdir(path):
            os.makedirs(path)

        self._parent = parent
        self._user_config = MultiUserConfig(
            NAMEMAP,
            path=path,
            defaults=DEFAULTS,
            load=True,
            version=CONF_VERSION,
            backup=True,
            raw_mode=True,
        )
        self._site_config = None
        self._project_configs = {}  # Cache project configurations

        # self.load_config()
        # self._remove_old_spyder_config_location()

    def load_config(self):
        pass
        # Main configuration instance
        # try:
        #     self._global_config = UserConfig(
        #         'spyder',
        #         defaults=DEFAULTS,
        #         load=True,
        #         version=CONF_VERSION,
        #         subfolder=SUBFOLDER,
        #         backup=True,
        #         raw_mode=True)
        # except Exception:
        #     self._global_config = UserConfig(
        #         'spyder',
        #         defaults=DEFAULTS,
        #         load=False,
        #         version=CONF_VERSION,
        #         subfolder=SUBFOLDER,
        #         backup=True,
        #         raw_mode=True)

    def _remove_old_spyder_config_location(self):
        """Removing old .spyder.ini location."""
        # old_location = osp.join(get_home_dir(), '.spyder.ini')
        # if osp.isfile(old_location):
        #     os.remove(old_location)

    def get_user_config_path(self):
        """TODO:"""
        base_path = get_conf_path()
        path = osp.join(base_path, 'app', 'config')
        if not osp.isdir(path):
            os.makedirs(path)

        return path

    def get_project_config_path(self, project_root):
        """TODO:"""

    def get_system_config_path(self, project_root):
        """TODO:"""

    def items(self, section):
        """"""
        return self._user_config.items(section)

    def options(self, section):
        return self._user_config.options(section)

    def get(self, *args, **kwargs):
        """"""
        # TODO: User project or site config as needed
        return self._user_config.get(*args, **kwargs)

    def set(self, *args, **kwargs):
        """"""
        # TODO: User project or site config as needed
        self._user_config.set(*args, **kwargs)

    def get_default(self, section, option):
        return self._user_config.get_default(section, option)

    def remove_section(self, section):
        """Remove `section` and all options within it."""
        self._user_config.remove_section(section)

    def remove_option(self, section, option):
        """Remove `option` from `section`."""
        self._user_config.remove_option(section, option)

    def reset_to_defaults(self):
        """"""
        self._user_config.reset_to_defaults()


class MultiUserConfig(object):
    """
    Multi user config class based on UserConfig class.

    This class provides the same interface as UserConfig but allows splitting
    the configuration sections and options among several files.

    The `name` is now a `namemap` where the sections and options per file name
    are defined.
    """

    def __init__(self, namemap, path, defaults=None, load=True, version=None,
                 backup=False, raw_mode=False, remove_obsolete=False):
        """TODO:"""
        self._namemap = self._check_namemap(namemap)
        self._path = path
        self._defaults = defaults
        self._load = load
        self._version = version
        self._backup = backup
        self._raw_mode = 1 if raw_mode else 0
        self._remove_obsolete = remove_obsolete

        self._configs_map = {}
        self._config_defaults_map = self._get_defaults_for_namemap(defaults,
                                                                   namemap)

        self._config_kwargs = {
            'path': path,
            'defaults': defaults,
            'load': load,
            'version': version,
            'backup': backup,
            'raw_mode': raw_mode,
            'remove_obsolete': remove_obsolete,
        }

        for name in namemap:
            defaults = self._config_defaults_map.get(name)
            mod_kwargs = {
                'name': name,
                'defaults': defaults,
            }
            new_kwargs = self._config_kwargs.copy()
            new_kwargs.update(mod_kwargs)
            self._configs_map[name] = UserConfig(**new_kwargs)

    def _get_config(self, section, option):
        """"""
        if option is None:
            return self._configs_map['main']

        for _, config in self._configs_map.items():
            if section is None:
                section = config.DEFAULT_SECTION_NAME

            if config.has_option(section, option):
                return config

        if config is None:
            return self._configs_map['main']

    def _check_namemap(self, namemap):
        """TODO:"""
        pass
        # Check it is not repeated
        # Check filemap names are not repeated or overide default name
        return namemap

    @staticmethod
    def _get_section_from_defaults(defaults, section):
        """TODO:"""
        for sec, options in defaults:
            if section == sec:
                value = options
                break
        else:
            raise ValueError('section "{}" not found!'.format(section))

        return value

    @staticmethod
    def _get_option_from_defaults(defaults, section, option):
        """TODO:"""
        value = None
        for sec, options in defaults:
            if section == sec:
                value = options.get(option, None)  # Change to No Default!
                break
        # else:
        #     raise ValueError('option "{}" not found in section "{}"!'.format(
        #             option, section))

        return value

    @staticmethod
    def _remove_section_from_defaults(defaults, section):
        """TODO:"""
        idx_remove = None
        for idx, (sec, _) in enumerate(defaults):
            if section == sec:
                idx_remove = idx
                break

        if idx_remove is not None:
            defaults.pop(idx)

    @staticmethod
    def _remove_option_from_defaults(defaults, section, option):
        """TODO:"""
        for sec, options in defaults:
            if section == sec:
                if option in options:
                    options.pop(option)
                    break

    @classmethod
    def _get_defaults_for_namemap(cls, defaults, namemap):
        """TODO:"""
        namemap_config = {}
        defaults_copy = copy.deepcopy(defaults)

        for name, sec_opts in namemap.items():
            default_map_for_name = []
            if len(sec_opts) == 0:
                namemap_config[name] = defaults_copy
            else:
                for section, options in sec_opts:
                    if len(options) == 0:
                        # Use all on section
                        sec = cls._get_section_from_defaults(defaults_copy,
                                                            section)

                        # Remove section from defaults
                        cls._remove_section_from_defaults(defaults_copy,
                                                          section)

                    else:
                        # Iterate and pop!
                        sec = {}
                        for opt in options:
                            val = cls._get_option_from_defaults(defaults_copy,
                                                                section, opt)
                            sec[opt] = val

                            # Remove option from defaults
                            cls._remove_option_from_defaults(defaults_copy,
                                                             section, opt)

                    # Add to config map
                    default_map_for_name.append((section, sec))

                namemap_config[name] = default_map_for_name

        return namemap_config

    def items(self, section):
        """"""
        config = self._get_config(section, None)
        if config is None:
            config = self._configs_map['main']

        return config.items(section=section)

    def options(self, section):
        """"""
        config = self._get_config(section, None)
        return config.options(section=section)

    def get_default(self, section, option):
        config = self._get_config(section, None)
        if config is None:
            config = self._configs_map['main']
        return config.get_default(section, option)

    def get(self, section, option, default=NoDefault):
        """"""
        config = self._get_config(section, option)
        
        if config is None:
            config = self._configs_map['main']

        return config.get(section=section, option=option, default=default)

    def set(self, section, option, value, verbose=False, save=True):
        """"""
        config = self._get_config(section, option)
        if config is None:
            config = self._configs_map['main']
        config.set(section=section, option=option, value=value,
                   verbose=verbose, save=save)

    def reset_to_defaults(self):
        """"""
        for _, config in self._configs_map.items():
            config.reset_to_defaults()

    def remove_section(self, section):
        """Remove `section` and all options within it."""
        config = self._get_config(section, None)
        if config is None:
            config = self._configs_map['main']
        config.remove_section(section)

    def remove_option(self, section, option):
        """Remove `option` from `section`."""
        config = self._get_config(section, option)
        if config is None:
            config = self._configs_map['main']
        config.remove_option(section, option)

    def cleanup(self):
        """Remove .ini files associated to configurations."""
        for config in self._configs_map:
            os.remove(config.get_config_path())


NAMEMAP = {
    # Empty container object means use the rest of defaults
    'main': {},
    # Splitting these files makes sense for projects, we might as well
    # apply the same split for the app global config
    # These options change on spyder startup, not good for version control
    'transient': [
        ('main', [
            'crash',
            'current_version',
            'historylog_filename',
            'window/state',
            'window/size',
            # 'window/position',
            'window/prefs_dialog_size',
            'last_visible_toolbars',
            'completion/size',
            ]
        ),
        ('appearance', [
            'windows_style',
            ]
        ),
        ('editor', [
            'splitter_state',
            'recent_files',
            'filenames',
            'layout_settings',
            ]
        ),
        ('explorer', [
            'file_associations',
        ]),
        ('find_in_files', [
            'search_text',
            'path_history'
        ]),
        ('online_help', [
            'zoom_factor',
        ]),
        ('outline_explorer', [
            'expanded_state',
            'scrollbar_position',
            ],
        ),
        ('project_explorer', [
            'scrollbar_position',
        ]),
        ('quick_layouts', []),
        ('run', [
            'configurations',
        ]),
        ('workingdir', [
            'startup/fixed_directory',
            'console/fixed_directory'
        ]),        
    ]
}


CONF = ConfigurationManager()

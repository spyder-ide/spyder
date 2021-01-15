# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
This module provides user configuration file management features for Spyder.

It is based on the ConfigParser module present in the standard library.
"""

from __future__ import print_function, unicode_literals

# Standard library imports
import ast
import copy
import io
import os
import os.path as osp
import re
import shutil
import time

# Local imports
from spyder.config.base import get_conf_path, get_module_source_path
from spyder.py3compat import configparser as cp
from spyder.py3compat import is_text_string, PY2, to_text_string
from spyder.utils.programs import check_version


# ============================================================================
# Auxiliary classes
# ============================================================================
class NoDefault:
    pass


# ============================================================================
# Defaults class
# ============================================================================
class DefaultsConfig(cp.ConfigParser, object):
    """
    Class used to save defaults to a file and as UserConfig base class.
    """

    def __init__(self, name, path):
        """
        Class used to save defaults to a file and as UserConfig base class.
        """
        if PY2:
            super(DefaultsConfig, self).__init__()
        else:
            super(DefaultsConfig, self).__init__(interpolation=None)

        self._name = name
        self._path = path

        if not osp.isdir(osp.dirname(self._path)):
            os.makedirs(osp.dirname(self._path))

    def _write(self, fp):
        """
        Write method for Python 2.

        The one from configparser fails for non-ascii Windows accounts.
        """
        if self._defaults:
            fp.write('[{}]\n'.format(cp.DEFAULTSECT))
            for (key, value) in self._defaults.items():
                value_plus_end_of_line = str(value).replace('\n', '\n\t')
                fp.write('{} = {}\n'.format(key, value_plus_end_of_line))

            fp.write('\n')

        for section in self._sections:
            fp.write('[{}]\n'.format(section))
            for (key, value) in self._sections[section].items():
                if key == '__name__':
                    continue

                if (value is not None) or (self._optcre == self.OPTCRE):
                    value = to_text_string(value)
                    value_plus_end_of_line = value.replace('\n', '\n\t')
                    key = ' = '.join((key, value_plus_end_of_line))

                fp.write('{}\n'.format(key))

            fp.write('\n')

    def _set(self, section, option, value, verbose):
        """Set method."""
        if not self.has_section(section):
            self.add_section(section)

        if not is_text_string(value):
            value = repr(value)

        if verbose:
            text = '[{}][{}] = {}'.format(section, option, value)
            print(text)  # spyder: test-skip

        super(DefaultsConfig, self).set(section, option, value)

    def _save(self):
        """Save config into the associated .ini file."""
        fpath = self.get_config_fpath()

        def _write_file(fpath):
            with io.open(fpath, 'w', encoding='utf-8') as configfile:
                if PY2:
                    self._write(configfile)
                else:
                    self.write(configfile)

        # See spyder-ide/spyder#1086 and spyder-ide/spyder#1242 for background
        # on why this method contains all the exception handling.
        try:
            # The "easy" way
            _write_file(fpath)
        except EnvironmentError:
            try:
                # The "delete and sleep" way
                if osp.isfile(fpath):
                    os.remove(fpath)

                time.sleep(0.05)
                _write_file(fpath)
            except Exception as e:
                print('Failed to write user configuration file to disk, with '
                      'the exception shown below')  # spyder: test-skip
                print(e)  # spyder: test-skip

    def get_config_fpath(self):
        """Return the ini file where this configuration is stored."""
        path = self._path
        config_file = osp.join(path, '{}.ini'.format(self._name))
        return config_file

    def set_defaults(self, defaults):
        """Set default values and save to defaults folder location."""
        for section, options in defaults:
            for option in options:
                new_value = options[option]
                self._set(section, option, new_value, verbose=False)


# ============================================================================
# User config class
# ============================================================================
class UserConfig(DefaultsConfig):
    """
    UserConfig class, based on ConfigParser.

    Parameters
    ----------
    name: str
        Name of the config
    path: str
        Configuration file will be saved in path/%name%.ini
    defaults: {} or [(str, {}),]
        Dictionary containing options *or* list of tuples (sec_name, options)
    load: bool
        If a previous configuration file is found, load will take the values
        from this existing file, instead of using default values.
    version: str
        version of the configuration file in 'major.minor.micro' format.
    backup: bool
        A backup will be created on version changes and on initial setup.
    raw_mode: bool
        If `True` do not apply any automatic conversion on values read from
        the configuration.
    remove_obsolete: bool
        If `True`, values that were removed from the configuration on version
        change, are removed from the saved configuration file.

    Notes
    -----
    The 'get' and 'set' arguments number and type differ from the overriden
    methods. 'defaults' is an attribute and not a method.
    """
    DEFAULT_SECTION_NAME = 'main'

    def __init__(self, name, path, defaults=None, load=True, version=None,
                 backup=False, raw_mode=False, remove_obsolete=False,
                 external_plugin=False):
        """UserConfig class, based on ConfigParser."""
        super(UserConfig, self).__init__(name=name, path=path)

        self._load = load
        self._version = self._check_version(version)
        self._backup = backup
        self._raw = 1 if raw_mode else 0
        self._remove_obsolete = remove_obsolete
        self._external_plugin = external_plugin

        self._module_source_path = get_module_source_path('spyder')
        self._defaults_folder = 'defaults'
        self._backup_folder = 'backups'
        self._backup_suffix = '.bak'
        self._defaults_name_prefix = 'defaults'

        # This attribute is overriding a method from cp.ConfigParser
        self.defaults = self._check_defaults(defaults)

        if backup:
            self._make_backup()

        if load:
            # If config file already exists, it overrides Default options
            previous_fpath = self.get_previous_config_fpath()
            self._load_from_ini(previous_fpath)
            old_version = self.get_version(version)
            self._old_version = old_version

            # Save new defaults
            self._save_new_defaults(self.defaults)

            # Updating defaults only if major/minor version is different
            if (self._get_minor_version(version)
                    != self._get_minor_version(old_version)):

                if backup:
                    self._make_backup(version=old_version)

                self.apply_configuration_patches(old_version=old_version)

                # Remove deprecated options if major version has changed
                if remove_obsolete:
                    self._remove_deprecated_options(old_version)

                # Set new version number
                self.set_version(version, save=False)

            if defaults is None:
                # If no defaults are defined set .ini file settings as default
                self.set_as_defaults()

    # --- Helpers and checkers
    # ------------------------------------------------------------------------
    @staticmethod
    def _get_minor_version(version):
        """Return the 'major.minor' components of the version."""
        return version[:version.rfind('.')]

    @staticmethod
    def _get_major_version(version):
        """Return the 'major' component of the version."""
        return version[:version.find('.')]

    @staticmethod
    def _check_version(version):
        """Check version is compliant with format."""
        regex_check = re.match(r'^(\d+).(\d+).(\d+)$', version)
        if version is not None and regex_check is None:
            raise ValueError('Version number {} is incorrect - must be in '
                             'major.minor.micro format'.format(version))

        return version

    def _check_defaults(self, defaults):
        """Check if defaults are valid and update defaults values."""
        if defaults is None:
            defaults = [(self.DEFAULT_SECTION_NAME, {})]
        elif isinstance(defaults, dict):
            defaults = [(self.DEFAULT_SECTION_NAME, defaults)]
        elif isinstance(defaults, list):
            # Check is a list of tuples with strings and dictionaries
            for sec, options in defaults:
                assert is_text_string(sec)
                assert isinstance(options, dict)
                for opt, _ in options.items():
                    assert is_text_string(opt)
        else:
            raise ValueError('`defaults` must be a dict or a list of tuples!')

        # This attribute is overriding a method from cp.ConfigParser
        self.defaults = defaults

        if defaults is not None:
            self.reset_to_defaults(save=False)

        return defaults

    @classmethod
    def _check_section_option(cls, section, option):
        """Check section and option types."""
        if section is None:
            section = cls.DEFAULT_SECTION_NAME
        elif not is_text_string(section):
            raise RuntimeError("Argument 'section' must be a string")

        if not is_text_string(option):
            raise RuntimeError("Argument 'option' must be a string")

        return section

    def _make_backup(self, version=None, old_version=None):
        """
        Make a backup of the configuration file.

        If `old_version` is `None` a normal backup is made. If `old_version`
        is provided, then the backup was requested for minor version changes
        and appends the version number to the backup file.
        """
        fpath = self.get_config_fpath()
        fpath_backup = self.get_backup_fpath_from_version(
            version=version, old_version=old_version)
        path = os.path.dirname(fpath_backup)

        if not osp.isdir(path):
            os.makedirs(path)

        try:
            shutil.copyfile(fpath, fpath_backup)
        except IOError:
            pass

    def _load_from_ini(self, fpath):
        """Load config from the associated .ini file found at `fpath`."""
        try:
            if PY2:
                # Python 2
                if osp.isfile(fpath):
                    try:
                        with io.open(fpath, encoding='utf-8') as configfile:
                            self.readfp(configfile)
                    except IOError:
                        error_text = "Failed reading file", fpath
                        print(error_text)  # spyder: test-skip
            else:
                # Python 3
                self.read(fpath, encoding='utf-8')
        except cp.MissingSectionHeaderError:
            error_text = 'Warning: File contains no section headers.'
            print(error_text)  # spyder: test-skip

    def _load_old_defaults(self, old_version):
        """Read old defaults."""
        old_defaults = cp.ConfigParser()
        path, name = self.get_defaults_path_name_from_version(old_version)
        old_defaults.read(osp.join(path, name + '.ini'))
        return old_defaults

    def _save_new_defaults(self, defaults):
        """Save new defaults."""
        path, name = self.get_defaults_path_name_from_version()
        new_defaults = DefaultsConfig(name=name, path=path)
        if not osp.isfile(new_defaults.get_config_fpath()):
            new_defaults.set_defaults(defaults)
            new_defaults._save()

    def _update_defaults(self, defaults, old_version, verbose=False):
        """Update defaults after a change in version."""
        old_defaults = self._load_old_defaults(old_version)
        for section, options in defaults:
            for option in options:
                new_value = options[option]
                try:
                    old_val = old_defaults.get(section, option)
                except (cp.NoSectionError, cp.NoOptionError):
                    old_val = None

                if old_val is None or to_text_string(new_value) != old_val:
                    self._set(section, option, new_value, verbose)

    def _remove_deprecated_options(self, old_version):
        """
        Remove options which are present in the .ini file but not in defaults.
        """
        old_defaults = self._load_old_defaults(old_version)
        for section in old_defaults.sections():
            for option, _ in old_defaults.items(section, raw=self._raw):
                if self.get_default(section, option) is NoDefault:
                    try:
                        self.remove_option(section, option)
                        if len(self.items(section, raw=self._raw)) == 0:
                            self.remove_section(section)
                    except cp.NoSectionError:
                        self.remove_section(section)

    # --- Compatibility API
    # ------------------------------------------------------------------------
    def get_previous_config_fpath(self):
        """Return the last configuration file used if found."""
        return self.get_config_fpath()

    def get_config_fpath_from_version(self, version=None):
        """
        Return the configuration path for given version.

        If no version is provided, it returns the current file path.
        """
        return self.get_config_fpath()

    def get_backup_fpath_from_version(self, version=None, old_version=None):
        """
        Get backup location based on version.

        `old_version` can be used for checking compatibility whereas `version`
        relates to adding the version to the file name.

        To be overridden if versions changed backup location.
        """
        fpath = self.get_config_fpath()
        path = osp.join(osp.dirname(fpath), self._backup_folder)
        new_fpath = osp.join(path, osp.basename(fpath))
        if version is None:
            backup_fpath = '{}{}'.format(new_fpath, self._backup_suffix)
        else:
            backup_fpath = "{}-{}{}".format(new_fpath, version,
                                            self._backup_suffix)
        return backup_fpath

    def get_defaults_path_name_from_version(self, old_version=None):
        """
        Get defaults location based on version.

        To be overridden if versions changed defaults location.
        """
        version = old_version if old_version else self._version
        defaults_path = osp.join(osp.dirname(self.get_config_fpath()),
                                 self._defaults_folder)
        name = '{}-{}-{}'.format(
            self._defaults_name_prefix,
            self._name,
            version,
        )
        if not osp.isdir(defaults_path):
            os.makedirs(defaults_path)

        return defaults_path, name

    def apply_configuration_patches(self, old_version=None):
        """
        Apply any patch to configuration values on version changes.

        To be overridden if patches to configuration values are needed.
        """
        pass

    # --- Public API
    # ------------------------------------------------------------------------
    def get_version(self, version='0.0.0'):
        """Return configuration (not application!) version."""
        return self.get(self.DEFAULT_SECTION_NAME, 'version', version)

    def set_version(self, version='0.0.0', save=True):
        """Set configuration (not application!) version."""
        version = self._check_version(version)
        self.set(self.DEFAULT_SECTION_NAME, 'version', version, save=save)

    def reset_to_defaults(self, save=True, verbose=False, section=None):
        """Reset config to Default values."""
        for sec, options in self.defaults:
            if section == None or section == sec:
                for option in options:
                    value = options[option]
                    self._set(sec, option, value, verbose)
        if save:
            self._save()

    def set_as_defaults(self):
        """Set defaults from the current config."""
        self.defaults = []
        for section in self.sections():
            secdict = {}
            for option, value in self.items(section, raw=self._raw):
                secdict[option] = value
            self.defaults.append((section, secdict))

    def get_default(self, section, option):
        """
        Get default value for a given `section` and `option`.

        This is useful for type checking in `get` method.
        """
        section = self._check_section_option(section, option)
        for sec, options in self.defaults:
            if sec == section:
                if option in options:
                    value = options[option]
                    break
        else:
            value = NoDefault

        return value

    def get(self, section, option, default=NoDefault):
        """
        Get an option.

        Parameters
        ----------
        section: str
            Section name. If `None` is provide use the default section name.
        option: str
            Option name for `section`.
        default:
            Default value (if not specified, an exception will be raised if
            option doesn't exist).
        """
        section = self._check_section_option(section, option)

        if not self.has_section(section):
            if default is NoDefault:
                raise cp.NoSectionError(section)
            else:
                self.add_section(section)

        if not self.has_option(section, option):
            if default is NoDefault:
                raise cp.NoOptionError(option, section)
            else:
                self.set(section, option, default)
                return default

        value = super(UserConfig, self).get(section, option, raw=self._raw)

        default_value = self.get_default(section, option)
        if isinstance(default_value, bool):
            value = ast.literal_eval(value)
        elif isinstance(default_value, float):
            value = float(value)
        elif isinstance(default_value, int):
            value = int(value)
        elif is_text_string(default_value):
            if PY2:
                try:
                    value = value.decode('utf-8')
                    try:
                        # Some str config values expect to be eval after
                        # decoding
                        new_value = ast.literal_eval(value)
                        if is_text_string(new_value):
                            value = new_value
                    except (SyntaxError, ValueError):
                        pass
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
        else:
            try:
                # Lists, tuples, ...
                value = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                pass

        return value

    def set_default(self, section, option, default_value):
        """
        Set Default value for a given `section`, `option`.

        If no defaults exist, no default is created. To be able to set
        defaults, a call to set_as_defaults is needed to create defaults
        based on current values.
        """
        section = self._check_section_option(section, option)
        for sec, options in self.defaults:
            if sec == section:
                options[option] = default_value

    def set(self, section, option, value, verbose=False, save=True):
        """
        Set an `option` on a given `section`.

        If section is None, the `option` is added to the default section.
        """
        section = self._check_section_option(section, option)
        default_value = self.get_default(section, option)

        if default_value is NoDefault:
            # This let us save correctly string value options with
            # no config default that contain non-ascii chars in
            # Python 2
            if PY2 and is_text_string(value):
                value = repr(value)

            default_value = value
            self.set_default(section, option, default_value)

        if isinstance(default_value, bool):
            value = bool(value)
        elif isinstance(default_value, float):
            value = float(value)
        elif isinstance(default_value, int):
            value = int(value)
        elif not is_text_string(default_value):
            value = repr(value)

        self._set(section, option, value, verbose)
        if save:
            self._save()

    def remove_section(self, section):
        """Remove `section` and all options within it."""
        super(UserConfig, self).remove_section(section)
        self._save()

    def remove_option(self, section, option):
        """Remove `option` from `section`."""
        super(UserConfig, self).remove_option(section, option)
        self._save()

    def cleanup(self):
        """Remove .ini file associated to config."""
        os.remove(self.get_config_fpath())

    def to_list(self):
        """
        Return in list format.

        The format is [('section1', {'opt-1': value, ...}),
                       ('section2', {'opt-2': othervalue, ...}), ...]
        """
        new_defaults = []
        self._load_from_ini(self.get_config_fpath())
        for section in self._sections:
            sec_data = {}
            for (option, _) in self.items(section):
                sec_data[option] = self.get(section, option)
            new_defaults.append((section, sec_data))

        return new_defaults


class SpyderUserConfig(UserConfig):

    def get_previous_config_fpath(self):
        """
        Override method.

        Return the last configuration file used if found.
        """
        fpath = self.get_config_fpath()

        # We don't need to add the contents of the old spyder.ini to
        # the configuration of external plugins. This was the cause
        # of  part two (the shortcut conflicts) of issue
        # spyder-ide/spyder#11132
        if self._external_plugin:
            previous_paths = [fpath]
        else:
            previous_paths = [
                # >= 51.0.0
                fpath,
                # < 51.0.0
                os.path.join(get_conf_path(), 'spyder.ini'),
            ]

        for fpath in previous_paths:
            if osp.isfile(fpath):
                break

        return fpath

    def get_config_fpath_from_version(self, version=None):
        """
        Override method.

        Return the configuration path for given version.

        If no version is provided, it returns the current file path.
        """
        if version is None or self._external_plugin:
            fpath = self.get_config_fpath()
        elif check_version(version, '51.0.0', '<'):
            fpath = osp.join(get_conf_path(), 'spyder.ini')
        else:
            fpath = self.get_config_fpath()

        return fpath

    def get_backup_fpath_from_version(self, version=None, old_version=None):
        """
        Override method.

        Make a backup of the configuration file.
        """
        if old_version and check_version(old_version, '51.0.0', '<'):
            name = 'spyder.ini'
            fpath = os.path.join(get_conf_path(), name)
            if version is None:
                backup_fpath = "{}{}".format(fpath, self._backup_suffix)
            else:
                backup_fpath = "{}-{}{}".format(fpath, version,
                                                self._backup_suffix)
        else:
            super_class = super(SpyderUserConfig, self)
            backup_fpath = super_class.get_backup_fpath_from_version(
                version, old_version)

        return backup_fpath

    def get_defaults_path_name_from_version(self, old_version=None):
        """
        Override method.

        Get defaults location based on version.
        """
        if old_version:
            if check_version(old_version, '51.0.0', '<'):
                name = '{}-{}'.format(self._defaults_name_prefix, old_version)
                path = osp.join(get_conf_path(), 'defaults')
            else:
                super_class = super(SpyderUserConfig, self)
                path, name = super_class.get_defaults_path_name_from_version(
                    old_version)
        else:
            super_class = super(SpyderUserConfig, self)
            path, name = super_class.get_defaults_path_name_from_version()

        return path, name

    def apply_configuration_patches(self, old_version=None):
        """
        Override method.

        Apply any patch to configuration values on version changes.
        """
        self._update_defaults(self.defaults, old_version)

        if self._external_plugin:
            return
        if old_version and check_version(old_version, '44.1.0', '<'):
            run_lines = to_text_string(self.get('ipython_console',
                                                'startup/run_lines'))
            if run_lines is not NoDefault:
                run_lines = run_lines.replace(',', '; ')
                self.set('ipython_console', 'startup/run_lines', run_lines)


class MultiUserConfig(object):
    """
    Multiuser config class which emulates the basic UserConfig interface.

    This class provides the same basic interface as UserConfig but allows
    splitting the configuration sections and options among several files.

    The `name` is now a `name_map` where the sections and options per file name
    are defined.
    """
    DEFAULT_FILE_NAME = 'spyder'

    def __init__(self, name_map, path, defaults=None, load=True, version=None,
                 backup=False, raw_mode=False, remove_obsolete=False,
                 external_plugin=False):
        """Multi user config class based on UserConfig class."""
        self._name_map = self._check_name_map(name_map)
        self._path = path
        self._defaults = defaults
        self._load = load
        self._version = version
        self._backup = backup
        self._raw_mode = 1 if raw_mode else 0
        self._remove_obsolete = remove_obsolete
        self._external_plugin = external_plugin

        self._configs_map = {}
        self._config_defaults_map = self._get_defaults_for_name_map(defaults,
                                                                    name_map)
        self._config_kwargs = {
            'path': path,
            'defaults': defaults,
            'load': load,
            'version': version,
            'backup': backup,
            'raw_mode': raw_mode,
            'remove_obsolete': False,  # This will be handled later on if True
            'external_plugin': external_plugin
        }

        for name in name_map:
            defaults = self._config_defaults_map.get(name)
            mod_kwargs = {
                'name': name,
                'defaults': defaults,
            }
            new_kwargs = self._config_kwargs.copy()
            new_kwargs.update(mod_kwargs)
            config_class = self.get_config_class()
            self._configs_map[name] = config_class(**new_kwargs)

        # Remove deprecated options if major version has changed
        default_config = self._configs_map.get(self.DEFAULT_FILE_NAME)
        major_ver = default_config._get_major_version(version)
        major_old_ver = default_config._get_major_version(
            default_config._old_version)

        # Now we can apply remove_obsolete
        if remove_obsolete or major_ver != major_old_ver:
            for _, config in self._configs_map.items():
                config._remove_deprecated_options(config._old_version)

    def _get_config(self, section, option):
        """Get the correct configuration based on section and option."""
        # Check the filemap first
        name = self._get_name_from_map(section, option)
        config_value = self._configs_map.get(name, None)

        if config_value is None:
            config_value = self._configs_map[self.DEFAULT_FILE_NAME]
        return config_value

    def _check_name_map(self, name_map):
        """Check `name_map` follows the correct format."""
        # Check section option paris are not repeated
        sections_options = []
        for _, sec_opts in name_map.items():
            for section, options in sec_opts:
                for option in options:
                    sec_opt = (section, option)
                    if sec_opt not in sections_options:
                        sections_options.append(sec_opt)
                    else:
                        error_msg = (
                            'Different files are holding the same '
                            'section/option: "{}/{}"!'.format(section, option)
                        )
                        raise ValueError(error_msg)
        return name_map

    @staticmethod
    def _get_section_from_defaults(defaults, section):
        """Get the section contents from the defaults."""
        for sec, options in defaults:
            if section == sec:
                value = options
                break
        else:
            raise ValueError('section "{}" not found!'.format(section))

        return value

    @staticmethod
    def _get_option_from_defaults(defaults, section, option):
        """Get the section,option value from the defaults."""
        value = NoDefault
        for sec, options in defaults:
            if section == sec:
                value = options.get(option, NoDefault)
                break
        return value

    @staticmethod
    def _remove_section_from_defaults(defaults, section):
        """Remove section from defaults."""
        idx_remove = None
        for idx, (sec, _) in enumerate(defaults):
            if section == sec:
                idx_remove = idx
                break

        if idx_remove is not None:
            defaults.pop(idx)

    @staticmethod
    def _remove_option_from_defaults(defaults, section, option):
        """Remove section,option from defaults."""
        for sec, options in defaults:
            if section == sec:
                if option in options:
                    options.pop(option)
                    break

    def _get_name_from_map(self, section=None, option=None):
        """
        Search for section and option on the name_map and return the name.
        """
        for name, sec_opts in self._name_map.items():
            # Ignore the main section
            default_sec_name = self._configs_map.get(name).DEFAULT_SECTION_NAME
            if name == default_sec_name:
                continue
            for sec, options in sec_opts:
                if sec == section:
                    if len(options) == 0:
                        return name
                    else:
                        for opt in options:
                            if opt == option:
                                return name

    @classmethod
    def _get_defaults_for_name_map(cls, defaults, name_map):
        """Split the global defaults using the name_map."""
        name_map_config = {}
        defaults_copy = copy.deepcopy(defaults)

        for name, sec_opts in name_map.items():
            default_map_for_name = []
            if len(sec_opts) == 0:
                name_map_config[name] = defaults_copy
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
                            if val is not NoDefault:
                                sec[opt] = val

                            # Remove option from defaults
                            cls._remove_option_from_defaults(defaults_copy,
                                                             section, opt)

                    # Add to config map
                    default_map_for_name.append((section, sec))

                name_map_config[name] = default_map_for_name

        return name_map_config

    def get_config_class(self):
        """Return the UserConfig class to use."""
        return SpyderUserConfig

    def sections(self):
        """Return all sections of the configuration file."""
        sections = set()
        for _, config in self._configs_map.items():
            for section in config.sections():
                sections.add(section)

        return list(sorted(sections))

    def items(self, section):
        """Return all the items option/values for the given section."""
        config = self._get_config(section, None)
        if config is None:
            config = self._configs_map[self.DEFAULT_FILE_NAME]

        if config.has_section(section):
            return config.items(section=section)
        else:
            return None

    def options(self, section):
        """Return all the options for the given section."""
        config = self._get_config(section, None)
        return config.options(section=section)

    def get_default(self, section, option):
        """
        Get Default value for a given `section` and `option`.

        This is useful for type checking in `get` method.
        """
        config = self._get_config(section, option)
        if config is None:
            config = self._configs_map[self.DEFAULT_FILE_NAME]
        return config.get_default(section, option)

    def get(self, section, option, default=NoDefault):
        """
        Get an `option` on a given `section`.

        If section is None, the `option` is requested from default section.
        """
        config = self._get_config(section, option)

        if config is None:
            config = self._configs_map[self.DEFAULT_FILE_NAME]

        return config.get(section=section, option=option, default=default)

    def set(self, section, option, value, verbose=False, save=True):
        """
        Set an `option` on a given `section`.

        If section is None, the `option` is added to the default section.
        """
        config = self._get_config(section, option)
        config.set(section=section, option=option, value=value,
                   verbose=verbose, save=save)

    def reset_to_defaults(self, section=None):
        """Reset configuration to Default values."""
        for _, config in self._configs_map.items():
            config.reset_to_defaults(section=section)

    def remove_section(self, section):
        """Remove `section` and all options within it."""
        config = self._get_config(section, None)
        config.remove_section(section)

    def remove_option(self, section, option):
        """Remove `option` from `section`."""
        config = self._get_config(section, option)
        config.remove_option(section, option)

    def cleanup(self):
        """Remove .ini files associated to configurations."""
        for _, config in self._configs_map.items():
            os.remove(config.get_config_fpath())


class PluginConfig(UserConfig):
    """Plugin configuration handler."""


class PluginMultiConfig(MultiUserConfig):
    """Plugin configuration handler with multifile support."""

    def get_config_class(self):
        return PluginConfig

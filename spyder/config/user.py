# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# ----------------------------------------------------------------------------

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
from spyder.config.base import get_module_source_path
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
                fp.write('{} = {}\n'.format((key, value_plus_end_of_line)))

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
        # See spyder-ide/spyder#1086 and spyder-ide/spyder#1242 for background
        # on why this method contains all the exception handling.
        fpath = self.get_config_path()

        def _write_file(fpath):
            with io.open(fpath, 'w', encoding='utf-8') as configfile:
                if PY2:
                    self._write(configfile)
                else:
                    self.write(configfile)
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

    def get_config_path(self):
        """
        Create a .ini filename located in `self._path`.

        This .ini files stores the global preferences.
        """
        path = self._path
        config_file = osp.join(path, '{}.ini'.format(self._name))
        return config_file

    def set_defaults(self, defaults):
        """Set default values and save to defaults folder location."""
        for section, options in defaults:
            for option in options:
                new_value = options[option]
                self._set(section, option, new_value, verbose=False)


class UserConfigPatches(object):
    """
    This mixin is used for the global config to define how old versions
    should be handled.
    """


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
        dictionnary containing options *or* list of tuples (sec_name, options)
    version: str
        version of the configuration file in major.minor.micro format.

    Notes
    -----
    The 'get' and 'set' arguments number and type differ from the overriden
    methods.
    """
    DEFAULT_SECTION_NAME = 'main'

    def __init__(self, name, path, defaults=None, load=True, version=None,
                 backup=False, raw_mode=False, remove_obsolete=False):
        """UserConfig class, based on ConfigParser."""
        super(UserConfig, self).__init__(name=name, path=path)

        self._load = load
        self._version = self._check_version(version)
        self._backup = backup
        self._raw = 1 if raw_mode else 0
        self._remove_obsolete = remove_obsolete
        self._module_source_path = get_module_source_path('spyder')

        self._defaults_folder = 'defaults'
        self._backup_folder = 'backups'
        self._backup_suffix = '.bak'
        self._defaults_name_prefix = 'defaults'

        # This is overriding a method from cp.ConfigParser
        self.defaults = self._check_defaults(defaults)

        fpath = self.get_config_path()
        if load:
            # If config file already exists, it overrides Default options:
            self._load_from_ini()
            old_ver = self.get_version(version)
            _major = lambda _t: _t[:_t.find('.')]
            _minor = lambda _t: _t[:_t.rfind('.')]

            # Save new defaults
            self._save_new_defaults(defaults, version, path)

            # Updating defaults only if major/minor version is different
            if _minor(version) != _minor(old_ver):
                if backup:
                    try:
                        shutil.copyfile(fpath, "{}-{}.bak".format(fpath,
                                                                  old_ver))
                    except IOError:
                        pass

                # TODO: This logic needs to be implemented outside as this is
                # only valid for the global config not for plugins config
                if check_version(old_ver, '2.4.0', '<'):
                    self.reset_to_defaults(save=False)
                else:
                    self._update_defaults(defaults, old_ver)

                if check_version(old_ver, '44.1.0', '<'):
                    run_lines = to_text_string(self.get('ipython_console',
                                                        'startup/run_lines'))
                    if run_lines is not NoDefault:
                        run_lines = run_lines.replace(',', '; ')
                        self.set('ipython_console',
                                 'startup/run_lines', run_lines)

                # Remove deprecated options if major version has changed
                if remove_obsolete or _major(version) != _major(old_ver):
                    self._remove_deprecated_options(old_ver)

                # Set new version number
                self.set_version(version, save=False)

            if defaults is None:
                # If no defaults are defined, set .ini file settings as
                # default
                self.set_as_defaults()

        if backup:
            try:
                new_path = osp.join(osp.dirname(fpath), self._backup_folder)
                if not osp.isdir(new_path):
                    os.makedirs(new_path)
                new_fpath = osp.join(new_path, osp.basename(fpath))
                shutil.copyfile(fpath, '{}{}'.format(new_fpath,
                                                     self._backup_suffix))
            except IOError:
                pass

    def _check_version(self, version):
        """Check version is compliant with format."""
        regex_check = re.match(r'^(\d+).(\d+).(\d+)$', version)
        if version is not None and regex_check is None:
            raise ValueError('Version number {} is incorrect - must be in '
                             'major.minor.micro format'.format(version))

        return version

    def _check_defaults(self, defaults):
        """Check if defaults are valid and update defaults values."""
        if isinstance(defaults, dict):
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

        # This is overriding a method
        self.defaults = defaults

        if defaults is not None:
            self.reset_to_defaults(save=False)

        return defaults

    def _check_section_option(self, section, option):
        """Check section and option types."""
        if section is None:
            section = self.DEFAULT_SECTION_NAME
        elif not is_text_string(section):
            raise RuntimeError("Argument 'section' must be a string")

        if not is_text_string(option):
            raise RuntimeError("Argument 'option' must be a string")

        return section

    def _load_from_ini(self):
        """Load config from the associated .ini file."""
        fpath = self.get_config_path()
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
        path, name = self._get_defaults_config_path_and_name(old_version)
        old_defaults.read(osp.join(path, name))
        return old_defaults

    def _get_defaults_config_path_and_name(self, version):
        """
        Helper to provide the correct name of defaults file based on version.
        """
        path = osp.dirname(self.get_config_path())
        if check_version(version, '3.0.0', '<='):
            name = '{}-{}.ini'.format(self._defaults_name_prefix,
                                      'old_version')
            path = self._module_source_path
        elif check_version(version, '52.0.0', '<'):
            name = '{}-{}.ini'.format(self._defaults_name_prefix,
                                      'old_version')
        else:
            name = '{}-{}-{}.ini'.format(self._defaults_name_prefix,
                                         self._name, 'old_version')

        defaults_path = osp.join(path)
        return defaults_path, name

    def _save_new_defaults(self, defaults, new_version, path):
        """Save new defaults."""
        path = osp.join(path, 'defaults')
        if not osp.isdir(path):
            os.makedirs(path)

        # Example: 'defaults-spyder-53'
        name = '{}-{}-{}'.format(self._defaults_name_prefix, self._name,
                                 new_version)
        new_defaults = DefaultsConfig(name=name, path=path)
        if not osp.isfile(new_defaults.get_config_path()):
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
        Get Default value for a given `section` and `option`.

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
        os.remove(self.get_config_path())


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
        """Multi user config class based on UserConfig class."""
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
        """Get the correct configuration based on section and option."""
        # Check the filemap first
        name = self._get_name_from_map(section, option)
        config_value = self._configs_map.get(name, None)

        if config_value is None:
            config_value = self._configs_map['main']
        return config_value

    def _check_namemap(self, namemap):
        """Check `namemap` follows the correct format."""
        pass
        # Check it is not repeated
        # Check filemap names are not repeated or overide default name
        return namemap

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
        Search for section and option on the namemap and return the name.
        """
        for name, sec_opts in self._namemap.items():
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
    def _get_defaults_for_namemap(cls, defaults, namemap):
        """Split the global defaults using the namemap."""
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
                            if val is not NoDefault:
                                sec[opt] = val

                            # Remove option from defaults
                            cls._remove_option_from_defaults(defaults_copy,
                                                             section, opt)

                    # Add to config map
                    default_map_for_name.append((section, sec))

                namemap_config[name] = default_map_for_name

        return namemap_config

    def items(self, section):
        """Return all the items option/values for the given section."""
        config = self._get_config(section, None)
        if config is None:
            config = self._configs_map['main']

        return config.items(section=section)

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
            config = self._configs_map['main']
        return config.get_default(section, option)

    def get(self, section, option, default=NoDefault):
        """
        Get an `option` on a given `section`.

        If section is None, the `option` is requested from default section.
        """
        config = self._get_config(section, option)

        if config is None:
            config = self._configs_map['main']

        return config.get(section=section, option=option, default=default)

    def set(self, section, option, value, verbose=False, save=True):
        """
        Set an `option` on a given `section`.

        If section is None, the `option` is added to the default section.
        """
        config = self._get_config(section, option)
        config.set(section=section, option=option, value=value,
                   verbose=verbose, save=save)

    def reset_to_defaults(self):
        """Reset configuration to Default values."""
        for _, config in self._configs_map.items():
            config.reset_to_defaults()

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
        for config in self._configs_map:
            os.remove(config.get_config_path())

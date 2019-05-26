# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
This module provides user configuration file management features for Spyder

It's based on the ConfigParser module (present in the standard library).
"""

from __future__ import print_function

# Std imports
import ast
import os
import os.path as osp
import re
import shutil
import time

# Local imports
from spyder.config.base import (get_conf_path, get_home_dir,
                                get_module_source_path)
from spyder.utils.programs import check_version
from spyder.py3compat import configparser as cp
from spyder.py3compat import PY2, is_text_string, to_text_string

# Std imports for Python 2
if PY2:
    import codecs


#==============================================================================
# Auxiliary classes
#==============================================================================
class NoDefault:
    pass


#==============================================================================
# Defaults class
#==============================================================================
class DefaultsConfig(cp.ConfigParser):
    """
    Class used to save defaults to a file and as base class for
    UserConfig
    """
    def __init__(self, name, subfolder):
        if PY2:
            cp.ConfigParser.__init__(self)
        else:
            cp.ConfigParser.__init__(self, interpolation=None)
        self.name = name
        self.subfolder = subfolder

    def _write(self, fp):
        """
        Private write method for Python 2
        The one from configparser fails for non-ascii Windows accounts
        """
        if self._defaults:
            fp.write("[%s]\n" % cp.DEFAULTSECT)
            for (key, value) in self._defaults.items():
                fp.write("%s = %s\n" % (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")
        for section in self._sections:
            fp.write("[%s]\n" % section)
            for (key, value) in self._sections[section].items():
                if key == "__name__":
                    continue
                if (value is not None) or (self._optcre == self.OPTCRE):
                    value = to_text_string(value)
                    key = " = ".join((key, value.replace('\n', '\n\t')))
                fp.write("%s\n" % (key))
            fp.write("\n")

    def _set(self, section, option, value, verbose):
        """
        Private set method
        """
        if not self.has_section(section):
            self.add_section( section )
        if not is_text_string(value):
            value = repr( value )
        if verbose:
            print('%s[ %s ] = %s' % (section, option, value))  # spyder: test-skip
        cp.ConfigParser.set(self, section, option, value)

    def _save(self):
        """
        Save config into the associated .ini file
        """
        # See Issue 1086 and 1242 for background on why this
        # method contains all the exception handling.
        fname = self.filename()

        def _write_file(fname):
            if PY2:
                # Python 2
                with codecs.open(fname, 'w', encoding='utf-8') as configfile:
                    self._write(configfile)
            else:
                # Python 3
                with open(fname, 'w', encoding='utf-8') as configfile:
                    self.write(configfile)

        try:  # the "easy" way
            _write_file(fname)
        except EnvironmentError:
            try:  # the "delete and sleep" way
                if osp.isfile(fname):
                    os.remove(fname)
                time.sleep(0.05)
                _write_file(fname)
            except Exception as e:
                print("Failed to write user configuration file to disk, with "
                      "the exception shown below")  # spyder: test-skip
                print(e)  # spyder: test-skip

    def filename(self):
        """Defines the name of the configuration file to use."""
        # Needs to be done this way to be used by the project config.
        # To fix on a later PR
        self._filename = getattr(self, '_filename', None)
        self._root_path = getattr(self, '_root_path', None)

        if self._filename is None and self._root_path is None:
            return self._filename_global()
        else:
            return self._filename_projects()

    def _filename_projects(self):
        """Create a .ini filename located in the current project directory.
        This .ini files stores the specific project preferences for each
        project created with spyder.
        """
        return osp.join(self._root_path, self._filename)

    def _filename_global(self):
        """Create a .ini filename located in user home directory.
        This .ini files stores the global spyder preferences.
        """
        if self.subfolder is None:
            config_file = osp.join(get_home_dir(), '.%s.ini' % self.name)
            return config_file
        else:
            folder = get_conf_path()
            # Save defaults in a "defaults" dir of .spyder2 to not pollute it
            if 'defaults' in self.name:
                folder = osp.join(folder, 'defaults')
                if not osp.isdir(folder):
                    os.mkdir(folder)
            config_file = osp.join(folder, '%s.ini' % self.name)
            return config_file

    def set_defaults(self, defaults):
        for section, options in defaults:
            for option in options:
                new_value = options[ option ]
                self._set(section, option, new_value, False)


#==============================================================================
# User config class
#==============================================================================
class UserConfig(DefaultsConfig):
    """
    UserConfig class, based on ConfigParser
    name: name of the config
    defaults: dictionnary containing options
              *or* list of tuples (section_name, options)
    version: version of the configuration file (X.Y.Z format)
    subfolder: configuration file will be saved in %home%/subfolder/%name%.ini

    Note that 'get' and 'set' arguments number and type
    differ from the overriden methods
    """
    DEFAULT_SECTION_NAME = 'main'
    def __init__(self, name, defaults=None, load=True, version=None,
                 subfolder=None, backup=False, raw_mode=False,
                 remove_obsolete=False):
        DefaultsConfig.__init__(self, name, subfolder)
        self.raw = 1 if raw_mode else 0
        if (version is not None and
                re.match(r'^(\d+).(\d+).(\d+)$', version) is None):
            raise ValueError("Version number %r is incorrect - must be in X.Y.Z format" % version)
        if isinstance(defaults, dict):
            defaults = [ (self.DEFAULT_SECTION_NAME, defaults) ]
        self.defaults = defaults
        if defaults is not None:
            self.reset_to_defaults(save=False)
        fname = self.filename()
        if backup:
            try:
                shutil.copyfile(fname, "%s.bak" % fname)
            except IOError:
                pass
        if load:
            # If config file already exists, it overrides Default options:
            self.load_from_ini()
            old_ver = self.get_version(version)
            _major = lambda _t: _t[:_t.find('.')]
            _minor = lambda _t: _t[:_t.rfind('.')]
            # Save new defaults
            self._save_new_defaults(defaults, version, subfolder)
            # Updating defaults only if major/minor version is different
            if _minor(version) != _minor(old_ver):
                if backup:
                    try:
                        shutil.copyfile(fname, "%s-%s.bak" % (fname, old_ver))
                    except IOError:
                        pass
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
                # If no defaults are defined, set .ini file settings as default
                self.set_as_defaults()

    def get_version(self, version='0.0.0'):
        """Return configuration (not application!) version"""
        return self.get(self.DEFAULT_SECTION_NAME, 'version', version)

    def set_version(self, version='0.0.0', save=True):
        """Set configuration (not application!) version"""
        self.set(self.DEFAULT_SECTION_NAME, 'version', version, save=save)

    def load_from_ini(self):
        """
        Load config from the associated .ini file
        """
        try:
            if PY2:
                # Python 2
                fname = self.filename()
                if osp.isfile(fname):
                    try:
                        with codecs.open(fname, encoding='utf-8') as configfile:
                            self.readfp(configfile)
                    except IOError:
                        print("Failed reading file", fname)  # spyder: test-skip
            else:
                # Python 3
                self.read(self.filename(), encoding='utf-8')
        except cp.MissingSectionHeaderError:
            print("Warning: File contains no section headers.")  # spyder: test-skip

    def _load_old_defaults(self, old_version):
        """Read old defaults"""
        old_defaults = cp.ConfigParser()
        if check_version(old_version, '3.0.0', '<='):
            path = get_module_source_path('spyder')
        else:
            path = osp.dirname(self.filename())
        path = osp.join(path, 'defaults')
        old_defaults.read(osp.join(path, 'defaults-'+old_version+'.ini'))
        return old_defaults

    def _save_new_defaults(self, defaults, new_version, subfolder):
        """Save new defaults"""
        new_defaults = DefaultsConfig(name='defaults-'+new_version,
                                      subfolder=subfolder)
        if not osp.isfile(new_defaults.filename()):
            new_defaults.set_defaults(defaults)
            new_defaults._save()

    def _update_defaults(self, defaults, old_version, verbose=False):
        """Update defaults after a change in version"""
        old_defaults = self._load_old_defaults(old_version)
        for section, options in defaults:
            for option in options:
                new_value = options[ option ]
                try:
                    old_value = old_defaults.get(section, option)
                except (cp.NoSectionError, cp.NoOptionError):
                    old_value = None
                if old_value is None or \
                  to_text_string(new_value) != old_value:
                    self._set(section, option, new_value, verbose)

    def _remove_deprecated_options(self, old_version):
        """
        Remove options which are present in the .ini file but not in defaults
        """
        old_defaults = self._load_old_defaults(old_version)
        for section in old_defaults.sections():
            for option, _ in old_defaults.items(section, raw=self.raw):
                if self.get_default(section, option) is NoDefault:
                    try:
                        self.remove_option(section, option)
                        if len(self.items(section, raw=self.raw)) == 0:
                            self.remove_section(section)
                    except cp.NoSectionError:
                        self.remove_section(section)

    def cleanup(self):
        """
        Remove .ini file associated to config
        """
        os.remove(self.filename())

    def set_as_defaults(self):
        """
        Set defaults from the current config
        """
        self.defaults = []
        for section in self.sections():
            secdict = {}
            for option, value in self.items(section, raw=self.raw):
                secdict[option] = value
            self.defaults.append( (section, secdict) )

    def reset_to_defaults(self, save=True, verbose=False, section=None):
        """
        Reset config to Default values
        """
        for sec, options in self.defaults:
            if section == None or section == sec:
                for option in options:
                    value = options[ option ]
                    self._set(sec, option, value, verbose)
        if save:
            self._save()

    def _check_section_option(self, section, option):
        """
        Private method to check section and option types
        """
        if section is None:
            section = self.DEFAULT_SECTION_NAME
        elif not is_text_string(section):
            raise RuntimeError("Argument 'section' must be a string")
        if not is_text_string(option):
            raise RuntimeError("Argument 'option' must be a string")
        return section

    def get_default(self, section, option):
        """
        Get Default value for a given (section, option)
        -> useful for type checking in 'get' method
        """
        section = self._check_section_option(section, option)
        for sec, options in self.defaults:
            if sec == section:
                if option in options:
                    return options[ option ]
        else:
            return NoDefault

    def get(self, section, option, default=NoDefault):
        """
        Get an option
        section=None: attribute a default section name
        default: default value (if not specified, an exception
        will be raised if option doesn't exist)
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

        value = cp.ConfigParser.get(self, section, option, raw=self.raw)
        # Use type of default_value to parse value correctly
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
                        # Some str config values expect to be eval after decoding
                        new_value = ast.literal_eval(value)
                        if is_text_string(new_value):
                            value = new_value
                    except (SyntaxError, ValueError):
                        pass
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
        else:
            try:
                # lists, tuples, ...
                value = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                pass
        return value

    def set_default(self, section, option, default_value):
        """
        Set Default value for a given (section, option)
        -> called when a new (section, option) is set and no default exists
        """
        section = self._check_section_option(section, option)
        for sec, options in self.defaults:
            if sec == section:
                options[ option ] = default_value

    def set(self, section, option, value, verbose=False, save=True):
        """
        Set an option
        section=None: attribute a default section name
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
        cp.ConfigParser.remove_section(self, section)
        self._save()

    def remove_option(self, section, option):
        cp.ConfigParser.remove_option(self, section, option)
        self._save()

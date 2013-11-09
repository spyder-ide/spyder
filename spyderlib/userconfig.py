#!/usr/bin/env python
# -*- coding: utf-8 -*-

#    userconfig License Agreement (MIT License)
#    ------------------------------------------
#    
#    Copyright © 2009-2012 Pierre Raybaut
#    
#    Permission is hereby granted, free of charge, to any person
#    obtaining a copy of this software and associated documentation
#    files (the "Software"), to deal in the Software without
#    restriction, including without limitation the rights to use,
#    copy, modify, merge, publish, distribute, sublicense, and/or sell
#    copies of the Software, and to permit persons to whom the
#    Software is furnished to do so, subject to the following
#    conditions:
#    
#    The above copyright notice and this permission notice shall be
#    included in all copies or substantial portions of the Software.
#    
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#    OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#    OTHER DEALINGS IN THE SOFTWARE.


"""
userconfig
----------

The ``spyderlib.userconfig`` module provides user configuration file (.ini file)
management features based on ``ConfigParser`` (standard Python library).
"""

from __future__ import print_function

__version__ = '1.1.0'
__license__ = __doc__

import os
import re
import os.path as osp
import shutil
import time

from spyderlib.baseconfig import DEV, TEST
from spyderlib.utils import encoding
from spyderlib.py3compat import configparser as cp
from spyderlib.py3compat import is_text_string, PY2

def get_home_dir():
    """
    Return user home directory
    """
    try:
        # expanduser() returns a raw byte string which needs to be
        # decoded with the codec that the OS is using to represent file paths.
        path = encoding.to_unicode_from_fs(osp.expanduser('~'))
    except:
        path = ''
    for env_var in ('HOME', 'USERPROFILE', 'TMP'):
        if osp.isdir(path):
            break
        # os.environ.get() returns a raw byte string which needs to be
        # decoded with the codec that the OS is using to represent environment
        # variables.
        path = encoding.to_unicode_from_fs(os.environ.get(env_var, ''))
    if path:
        return path
    else:
        raise RuntimeError('Please define environment variable $HOME')


class NoDefault:
    pass


class UserConfig(cp.ConfigParser):
    """
    UserConfig class, based on ConfigParser
    name: name of the config
    defaults: dictionnary containing options
              *or* list of tuples (section_name, options)
    version: version of the configuration file (X.Y.Z format)
    subfolder: configuration file will be saved in %home%/subfolder/.%name%.ini
    
    Note that 'get' and 'set' arguments number and type
    differ from the overriden methods
    """
    DEFAULT_SECTION_NAME = 'main'
    def __init__(self, name, defaults=None, load=True, version=None,
                 subfolder=None, backup=False, raw_mode=False,
                 remove_obsolete=False):
        cp.ConfigParser.__init__(self)
        self.raw = 1 if raw_mode else 0
        self.subfolder = subfolder
        if (version is not None) and (re.match('^(\d+).(\d+).(\d+)$', version) is None):
            raise ValueError("Version number %r is incorrect - must be in X.Y.Z format" % version)
        self.name = name
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
            # Resetting to defaults only if major/minor version is different
            if _minor(version) != _minor(old_ver):
                if backup:
                    try:
                        shutil.copyfile(fname, "%s-%s.bak" % (fname, old_ver))
                    except IOError:
                        pass
                # Version has changed -> overwriting .ini file
                self.reset_to_defaults(save=False)
                if remove_obsolete or _major(version) != _major(old_ver):
                    self.__remove_deprecated_options()
                # Set new version number
                self.set_version(version, save=False)
            if defaults is None:
                # If no defaults are defined, set .ini file settings as default
                self.set_as_defaults()
        # In any case, the resulting config is saved in config file:
        # FIXME (Carlos): Commenting this for now because it's corrupting our
        # config on Windows when a user tries to open several files at once. Is
        # this really necessary?
        # self.__save()
        
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
                self.read(self.filename())
            else:
                # Python 3
                self.read(self.filename(), encoding='utf-8')
        except cp.MissingSectionHeaderError:
            print("Warning: File contains no section headers.")
        
    def __remove_deprecated_options(self):
        """
        Remove options which are present in the .ini file but not in defaults
        """
        for section in self.sections():
            for option, _ in self.items(section, raw=self.raw):
                if self.get_default(section, option) is NoDefault:
                    self.remove_option(section, option)
                    if len(self.items(section, raw=self.raw)) == 0:
                        self.remove_section(section)
        
    def __save(self):
        """
        Save config into the associated .ini file
        """
        # See Issue 1086 and 1242 for background on why this
        # method contains all the exception handling.
        fname = self.filename()

        def _write_file(fname):
            if PY2:
                # Python 2
                with open(fname, 'w') as configfile:
                    self.write(configfile)
            else:
                # Python 3
                with open(fname, 'w', encoding='utf-8') as configfile:
                    self.write(configfile)

        try: # the "easy" way
            _write_file(fname)
        except IOError:
            try: # the "delete and sleep" way
                if osp.isfile(fname):
                    os.remove(fname)
                time.sleep(0.05)
                _write_file(fname)
            except Exception as e:
                print("Failed to write user configuration file.")
                print("Please submit a bug report.")
                raise(e)

    def filename(self):
        """
        Create a .ini filename located in user home directory
        """
        if TEST is None:
            folder = get_home_dir()
        else:
            import tempfile
            folder = tempfile.gettempdir()
        w_dot = osp.join(folder, '.%s.ini' % self.name)
        if self.subfolder is None:
            return w_dot
        else:
            folder = osp.join(folder, self.subfolder)
            try:
                os.makedirs(folder)
            except os.error:
                # Folder (or one of its parents) already exists
                pass
            old, new = w_dot, osp.join(folder, '%s.ini' % self.name)
            if osp.isfile(old) and DEV is None:
                try:
                    if osp.isfile(new):
                        os.remove(old)
                    else:
                        os.rename(old, new)
                except OSError:
                    pass
            return new
        
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

    def reset_to_defaults(self, save=True, verbose=False):
        """
        Reset config to Default values
        """
        for section, options in self.defaults:
            for option in options:
                value = options[ option ]
                self.__set(section, option, value, verbose)
        if save:
            self.__save()
        
    def __check_section_option(self, section, option):
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
        section = self.__check_section_option(section, option)
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
        section = self.__check_section_option(section, option)

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
        default_value = self.get_default(section, option)
        if isinstance(default_value, bool):
            value = eval(value)
        elif isinstance(default_value, float):
            value = float(value)
        elif isinstance(default_value, int):
            value = int(value)
        else:
            if PY2 and is_text_string(default_value):
                try:
                    value = value.decode('utf-8')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
            try:
                # lists, tuples, ...
                value = eval(value)
            except:
                pass
        return value

    def __set(self, section, option, value, verbose):
        """
        Private set method
        """
        if not self.has_section(section):
            self.add_section( section )
        if not is_text_string(value):
            value = repr( value )
        if verbose:
            print('%s[ %s ] = %s' % (section, option, value))
        cp.ConfigParser.set(self, section, option, value)

    def set_default(self, section, option, default_value):
        """
        Set Default value for a given (section, option)
        -> called when a new (section, option) is set and no default exists
        """
        section = self.__check_section_option(section, option)
        for sec, options in self.defaults:
            if sec == section:
                options[ option ] = default_value

    def set(self, section, option, value, verbose=False, save=True):
        """
        Set an option
        section=None: attribute a default section name
        """
        section = self.__check_section_option(section, option)
        default_value = self.get_default(section, option)
        if default_value is NoDefault:
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
        self.__set(section, option, value, verbose)
        if save:
            self.__save()
            
    def remove_section(self, section):
        cp.ConfigParser.remove_section(self, section)
        self.__save()
            
    def remove_option(self, section, option):
        cp.ConfigParser.remove_option(self, section, option)
        self.__save()

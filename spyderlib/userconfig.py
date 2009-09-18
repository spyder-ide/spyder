# -*- coding: utf-8 -*-
"""
userconfig
==========

Module handling configuration files based on ConfigParser


userconfig License Agreement (MIT License)
------------------------------------------

Copyright (c) 2009 Pierre Raybaut

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

__version__ = '1.0.11'
__license__ = __doc__

import os, re
import os.path as osp
from ConfigParser import ConfigParser, MissingSectionHeaderError


def get_home_dir():
    """
    Return user home directory
    """
    try:
        path = osp.expanduser('~')
    except:
        path = ''
    for env_var in ('HOME', 'USERPROFILE', 'TMP'):
        if osp.isdir(path):
            break
        path = os.environ.get(env_var, '')
    if path:
        return path
    else:
        raise RuntimeError('Please define environment variable $HOME')

class NoDefault:
    pass

class UserConfig(ConfigParser):
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
    
    default_section_name = 'main'
    
    def __init__(self, name, defaults=None, load=True, version=None,
                 subfolder=None):
        ConfigParser.__init__(self)
        self.subfolder = subfolder
        if (version is not None) and (re.match('^(\d+).(\d+).(\d+)$', version) is None):
            raise RuntimeError("Version number %r is incorrect - must be in X.Y.Z format" % version)
        self.name = name
        if isinstance(defaults, dict):
            defaults = [ (self.default_section_name, defaults) ]
        self.defaults = defaults
        if defaults is not None:
            self.reset_to_defaults(save=False)
        if load:
            # If config file already exists, it overrides Default options:
            self.load_from_ini()
            if version != self.get_version(version):
                # Version has changed -> overwriting .ini file
                self.reset_to_defaults(save=False)
                self.__remove_deprecated_options()
                # Set new version number
                self.set_version(version, save=False)
            if defaults is None:
                # If no defaults are defined, set .ini file settings as default
                self.set_as_defaults()
        # In any case, the resulting config is saved in config file:
        self.__save()
        
    def get_version(self, version='0.0.0'):
        """Return configuration (not application!) version"""
        return self.get(self.default_section_name, 'version', version)
        
    def set_version(self, version='0.0.0', save=True):
        """Set configuration (not application!) version"""
        self.set(self.default_section_name, 'version', version, save=save)

    def load_from_ini(self):
        """
        Load config from the associated .ini file
        """
        try:
            self.read(self.filename())
        except MissingSectionHeaderError:
            print "Warning: File contains no section headers."
        
    def __remove_deprecated_options(self):
        """
        Remove options which are present in the .ini file but not in defaults
        """
        for section in self.sections():
            for option, _ in self.items(section):
                if self.get_default(section, option) is NoDefault:
                    self.remove_option(section, option)
                    if len(self.items(section)) == 0:
                        self.remove_section(section)
        
    def __save(self):
        """
        Save config into the associated .ini file
        """
        conf_file = file(self.filename(),'w')
        self.write(conf_file)
        conf_file.close()

    def filename(self):
        """
        Create a .ini filename located in user home directory
        """
        folder = get_home_dir()
        if self.subfolder is not None:
            folder = osp.join(folder, self.subfolder)
            try:
                os.makedirs(folder)
            except os.error:
                # Folder (or one of its parents) already exists
                pass
        return osp.join(folder, '.%s.ini' % self.name)
        
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
            for option, value in self.items(section):
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
            section = self.default_section_name
        elif not isinstance(section, (str, unicode)):
            raise RuntimeError, "Argument 'section' must be a string"
        if not isinstance(option, (str, unicode)):
            raise RuntimeError, "Argument 'option' must be a string"
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
                raise RuntimeError("Unknown section %r" % section)
            else:
                self.add_section(section)
        
        if not self.has_option(section, option):
            if default is NoDefault:
                raise RuntimeError("Unknown option %r" % option)
            else:
                self.set(section, option, default)
                return default
            
        value = ConfigParser.get(self, section, option)
        default_value = self.get_default(section, option)
        if isinstance(default_value, bool):
            value = eval(value)
        elif isinstance(default_value, float):
            value = float(value)
        elif isinstance(default_value, int):
            value = int(value)
        else:
            if isinstance(default_value, basestring):
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
        if not isinstance(value, (str, unicode)):
            value = repr( value )
        if verbose:
            print '%s[ %s ] = %s' % (section, option, value)
        ConfigParser.set(self, section, option, value)

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
        else:
            value = repr(value)
        self.__set(section, option, value, verbose)
        if save:
            self.__save()

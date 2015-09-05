# -*- coding: utf-8 -*-
#
# Copyright © 2013 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Module checking Spyder optional runtime dependencies"""


import os

# Local imports
from spyderlib.utils import programs


class Dependency(object):
    """Spyder's optional dependency

    version may starts with =, >=, > or < to specify the exact requirement ;
    multiple conditions may be separated by ';' (e.g. '>=0.13;<1.0')"""

    OK = 'OK'
    NOK = 'NOK'

    def __init__(self, modname, features, required_version,
                 installed_version=None):
        self.modname = modname
        self.features = features
        self.required_version = required_version
        if installed_version is None:
            try:
                self.installed_version = programs.get_module_version(modname)
            except ImportError:
                # Module is not installed
                self.installed_version = None
        else:
            self.installed_version = installed_version

    def check(self):
        """Check if dependency is installed"""
        return programs.is_module_installed(self.modname,
                                            self.required_version,
                                            self.installed_version)

    def get_installed_version(self):
        """Return dependency status (string)"""
        if self.check():
            return '%s (%s)' % (self.installed_version, self.OK)
        else:
            return '%s (%s)' % (self.installed_version, self.NOK)
    
    def get_status(self):
        """Return dependency status (string)"""
        if self.check():
            return self.OK
        else:
            return self.NOK


DEPENDENCIES = []

def add(modname, features, required_version, installed_version=None):
    """Add Spyder optional dependency"""
    global DEPENDENCIES
    for dependency in DEPENDENCIES:
        if dependency.modname == modname:
            raise ValueError("Dependency has already been registered: %s"\
                             % modname)
    DEPENDENCIES += [Dependency(modname, features, required_version,
                                installed_version)]

def check(modname):
    """Check if required dependency is installed"""
    global DEPENDENCIES
    for dependency in DEPENDENCIES:
        if dependency.modname == modname:
            return dependency.check()
    else:
        raise RuntimeError("Unkwown dependency %s" % modname)

def status():
    """Return a complete status of Optional Dependencies"""
    global DEPENDENCIES
    maxwidth = 0
    col1 = []
    col2 = []
    for dependency in DEPENDENCIES:
        title1 = dependency.modname
        title1 += ' ' + dependency.required_version
        col1.append(title1)
        maxwidth = max([maxwidth, len(title1)])
        col2.append(dependency.get_installed_version())
    text = ""
    for index in range(len(DEPENDENCIES)):
        text += col1[index].ljust(maxwidth) + ':  ' + col2[index] + os.linesep
    return text

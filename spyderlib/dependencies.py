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
    def __init__(self, modname, features, version=None, get_version_func=None):
        self.modname = modname
        self.features = features
        self.version = version
        self.get_version_func = get_version_func

    def check(self):
        """Check if dependency is installed"""
        return programs.is_module_installed(self.modname, self.version,
                                        get_version_func=self.get_version_func)

    def get_installed_version(self):
        """Return module installed version"""
        if self.get_version_func is None:
            return programs.get_module_version(self.modname)
        else:
            return self.get_version_func()

    def get_status(self):
        """Return dependency status (string)"""
        if self.check():
            status = 'OK'
            if self.version is None:
                status += ' (v%s)' % self.get_installed_version()
            return status
        else:
            return 'NOK (v%s)' % self.get_installed_version()


DEPENDENCIES = []

def add(modname, features, version=None, get_version_func=None):
    """Add Spyder optional dependency"""
    global DEPENDENCIES
    for dependency in DEPENDENCIES:
        if dependency.modname == modname:
            raise ValueError("Dependency has already been registered: %s"\
                             % modname)
    DEPENDENCIES += [Dependency(modname, features, version, get_version_func)]

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
        if dependency.version:
            title1 += ' ' + dependency.version
        col1.append(title1)
        maxwidth = max([maxwidth, len(title1)])
        col2.append(dependency.get_status())
    text = ""
    for index in range(len(DEPENDENCIES)):
        text += col1[index].ljust(maxwidth) + ':  ' + col2[index] + os.linesep
    return text

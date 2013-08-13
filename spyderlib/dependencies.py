# -*- coding: utf-8 -*-
#
# Copyright © 2013 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Module checking Spyder optional runtime dependencies"""

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
        return programs.check_module_version(self.modname, self.version,
                                             self.get_version_func)

    def get_status(self):
        """Return dependency status (string)"""
        if self.check():
            return 'OK'
        else:
            if self.get_version_func is None:
                actver = programs.get_module_version(self.modname)
            else:
                actver = self.get_version_func()
            return 'NOK (v%s)' % actver


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

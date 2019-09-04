# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Module checking Spyder runtime dependencies"""


import os

# Local imports
from spyder.utils import programs
from spyder.config.base import _


CLOUDPICKLE_REQVER = '>=0.5.0'
PYGMENTS_REQVER = '>=2.0'
QTCONSOLE_REQVER = '>=4.5.0'
NBCONVERT_REQVER = '>=4.0'
SPHINX_REQVER = '>=0.6.6'
PYLINT_REQVER = '>=0.25'
PSUTIL_REQVER = '>=0.3'
QTAWESOME_REQVER = '>=0.5.7'
QTPY_REQVER = '>=1.5.0'
PICKLESHARE_REQVER = '>=0.4'
PYZMQ_REQVER = '>=17'
CHARDET_REQVER = '>=2.0.0'
NUMPYDOC_REQVER = '>=0.6.0'
SPYDER_KERNELS_REQVER = '>=1.4.0'
QDARKSTYLE_REQVER = '>=2.7.0'
ATOMICWRITES_REQVER = '>=1.2.0'
DIFF_MATCH_PATCH_REQVER = '>=20181111'
WATCHDOG_REQVER = '>=0.9.0'
KEYRING_REQVER = '>=12.0.0'
PEXPECT_REQVER = '>=4.4.0'
PARAMIKO_REQVER = '>=2.4.0'
PYXDG_REQVER = '>=0.26'

DEPENDENCIES_BASE = [
    {'modname': "cloudpickle",
     'package_name': "cloudpickle",
     'features': _("Serialize variables in the IPython kernel to send to Spyder."),
     'required_version': CLOUDPICKLE_REQVER},
    {'modname': "pygments",
     'package_name': "pygments",
     'features': _("Syntax highlighting for Matlab, Julia and other file types"),
     'required_version': PYGMENTS_REQVER},
    {'modname': "qtconsole",
     'package_name': "qtconsole",
     'features': _("Integrate the IPython console"),
     'required_version': QTCONSOLE_REQVER},
    {'modname': "nbconvert",
     'package_name': "nbconvert",
     'features': _("Manipulate Jupyter notebooks on the Editor"),
     'required_version': NBCONVERT_REQVER},
    {'modname': "sphinx",
     'package_name': "sphinx",
     'features': _("Show help for objects in the Editor and Consoles in a dedicated pane"),
     'required_version': SPHINX_REQVER},
    {'modname': "pylint",
     'package_name': "pylint",
     'features': _("Static code analysis"),
     'required_version': PYLINT_REQVER},
    {'modname': "psutil",
     'package_name': "psutil",
     'features': _("CPU and memory usage info in the status bar"),
     'required_version': PSUTIL_REQVER},
    {'modname': "qtawesome",
     'package_name': "qtawesome",
     'features': _("To have an icon theme based on FontAwesome."),
     'required_version': QTAWESOME_REQVER},
    {'modname': "qtpy",
     'package_name': "qtpy",
     'features': _("Abstraction layer for Python Qt bindings so that Spyder can run on multiple Qt bindings and versions."),
     'required_version': QTPY_REQVER},
    {'modname': "pickleshare",
     'package_name': "pickleshare",
     'features': _("Show import completions on the Python consoles."),
     'required_version': PICKLESHARE_REQVER},
    {'modname': "pyzmq",
     'package_name': "pyzmq",
     'features': _("Client for the language server protocol (LSP)."),
     'required_version': PYZMQ_REQVER},
    {'modname': "chardet",
     'package_name': "chardet",
     'features': _("Character encoding auto-detection in Python."),
     'required_version': CHARDET_REQVER},
    {'modname': "numpydoc",
     'package_name': "numpydoc",
     'features': _("Used by Jedi to get function return types from Numpydocstrings."),
     'required_version': NUMPYDOC_REQVER},
    {'modname': "spyder-kernels",
     'package_name': "spyder-kernels",
     'features': _("Jupyter kernels for the Spyder console."),
     'required_version': SPYDER_KERNELS_REQVER},
    {'modname': "qdarkstyle",
     'package_name': "qdarkstyle",
     'features': _("Dark style for the entire interface"),
     'required_version': QDARKSTYLE_REQVER},
    {'modname': "atomicwrites",
     'package_name': "atomicwrites",
     'features': _("Atomic file writes."),
     'required_version': ATOMICWRITES_REQVER},
    {'modname': "diff_match_patch",
     'package_name': "diff_match_patch",
     'features': _("Compute text file diff changes during edition."),
     'required_version': DIFF_MATCH_PATCH_REQVER},
    {'modname': "watchdog",
     'package_name': "watchdog",
     'features': _("Watch file changes on project directories."),
     'required_version': WATCHDOG_REQVER},
    {'modname': "keyring",
     'package_name': "keyring",
     'features': _("Save Github credentials to report errors securely."),
     'required_version': KEYRING_REQVER},
    {'modname': "pexpect",
     'package_name': "pexpect",
     'features': _("Connect to remote kernels through SSH."),
     'required_version': PEXPECT_REQVER},
    {'modname': "paramiko",
     'package_name': "paramiko",
     'features': _("Connect to remote kernels through SSH."),
     'required_version': PARAMIKO_REQVER},
    {'modname': "pyxdg",
     'package_name': "pyxdg",
     'features': _("Parse `.desktop` files on Linux"),
     'required_version': PYXDG_REQVER}, ]

class Dependency(object):
    """Spyder's dependency

    version may starts with =, >=, > or < to specify the exact requirement ;
    multiple conditions may be separated by ';' (e.g. '>=0.13;<1.0')"""

    OK = 'OK'
    NOK = 'NOK'

    def __init__(self, modname, package_name, features, required_version,
                 installed_version=None, optional=False):
        self.modname = modname
        self.package_name = package_name
        self.features = features
        self.required_version = required_version
        self.optional = optional
        if installed_version is None:
            try:
                self.installed_version = programs.get_module_version(modname)
            except:
                # NOTE: Don't add any exception type here!
                # Modules can fail to import in several ways besides
                # ImportError
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


def add(modname, package_name, features, required_version,
        installed_version=None, optional=False):
    """Add Spyder dependency"""
    global DEPENDENCIES
    for dependency in DEPENDENCIES:
        if dependency.modname == modname:
            raise ValueError("Dependency has already been registered: %s"\
                             % modname)
    DEPENDENCIES += [Dependency(modname, package_name, features,
                                required_version,
                                installed_version, optional)]


def check(modname):
    """Check if required dependency is installed"""
    for dependency in DEPENDENCIES:
        if dependency.modname == modname:
            return dependency.check()
    else:
        raise RuntimeError("Unkwown dependency %s" % modname)


def status(deps=DEPENDENCIES, linesep=os.linesep):
    """Return a status of dependencies"""
    maxwidth = 0
    col1 = []
    col2 = []
    for dependency in deps:
        title1 = dependency.modname
        title1 += ' ' + dependency.required_version
        col1.append(title1)
        maxwidth = max([maxwidth, len(title1)])
        col2.append(dependency.get_installed_version())
    text = ""
    for index in range(len(deps)):
        text += col1[index].ljust(maxwidth) + ':  ' + col2[index] + linesep
    return text[:-1]


def missing_dependencies():
    """Return the status of missing dependencies (if any)"""
    missing_deps = []
    for dependency in DEPENDENCIES:
        if not dependency.check() and not dependency.optional:
            missing_deps.append(dependency)
    if missing_deps:
        return status(deps=missing_deps, linesep='<br>')
    else:
        return ""


def declare_dependencies():
    for dep in DEPENDENCIES_BASE:
        add(dep['modname'], dep['package_name'],
            dep['features'], dep['required_version'])

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Module checking Spyder runtime dependencies"""


import os
import sys

# Local imports
from spyder.utils import programs
from spyder.config.base import _
from spyder.config.utils import is_anaconda
from spyder.py3compat import PY2


# =============================================================================
# Kind of dependency
# =============================================================================
MANDATORY = 'mandatory'
OPTIONAL = 'optional'
PLUGIN = 'spyder plugins'


# =============================================================================
# Versions
# =============================================================================
# Hard dependencies
APPLAUNCHSERVICES_REQVER = '>=0.1.7'
ATOMICWRITES_REQVER = '>=1.2.0'
CHARDET_REQVER = '>=2.0.0'
CLOUDPICKLE_REQVER = '>=0.5.0'
COOKIECUTTER_REQVER = '>=1.6.0'
DIFF_MATCH_PATCH_REQVER = '>=20181111'
INTERVALTREE_REQVER = None
IPYTHON_REQVER = ">=4.0;<6.0" if PY2 else ">=4.0"
JEDI_REQVER = '=0.17.1'
KEYRING_REQVER = None
NBCONVERT_REQVER = '>=4.0'
NUMPYDOC_REQVER = '>=0.6.0'
PARAMIKO_REQVER = '>=2.4.0'
PARSO_REQVER = '=0.7.0'
PEXPECT_REQVER = '>=4.4.0'
PICKLESHARE_REQVER = '>=0.4'
PSUTIL_REQVER = '>=5.3'
PYGMENTS_REQVER = '>=2.0'
PYLINT_REQVER = '>=1.0'
PYLS_REQVER = '>=0.34.0;<1.0.0'
PYXDG_REQVER = '>=0.26'
PYZMQ_REQVER = '>=17'
QDARKSTYLE_REQVER = '>=2.8'
QTAWESOME_REQVER = '>=0.5.7'
QTCONSOLE_REQVER = '>=4.6.0'
QTPY_REQVER = '>=1.5.0'
RTREE_REQVER = '>=0.8.3'
SPHINX_REQVER = '>=0.6.6'
SPYDER_KERNELS_REQVER = '>=1.9.2;<1.10.0'
WATCHDOG_REQVER = None


# Optional dependencies
CYTHON_REQVER = '>=0.21'
MATPLOTLIB_REQVER = '>=2.0.0'
NUMPY_REQVER = '>=1.7'
PANDAS_REQVER = '>=0.13.1'
SCIPY_REQVER = '>=0.17.0'
SYMPY_REQVER = '>=0.7.3'


# =============================================================================
# Descriptions
# NOTE: We declare our dependencies in **alphabetical** order
# If some dependencies are limited to some systems only, add a 'display' key.
# See 'applaunchservices' for an example.
# =============================================================================
# List of descriptions
DESCRIPTIONS = [
    {'modname': "applaunchservices",
     'package_name': "applaunchservices",
     'features': _("Notify macOS that Spyder can open Python files"),
     'required_version': APPLAUNCHSERVICES_REQVER,
     'display': sys.platform == "darwin"},
    {'modname': "atomicwrites",
     'package_name': "atomicwrites",
     'features': _("Atomic file writes in the Editor"),
     'required_version': ATOMICWRITES_REQVER},
    {'modname': "chardet",
     'package_name': "chardet",
     'features': _("Character encoding auto-detection for the Editor"),
     'required_version': CHARDET_REQVER},
    {'modname': "cloudpickle",
     'package_name': "cloudpickle",
     'features': _("Handle communications between kernel and frontend"),
     'required_version': CLOUDPICKLE_REQVER},
    {'modname': "cookiecutter",
     'package_name': "cookiecutter",
     'features': _("Create projects from cookiecutter templates"),
     'required_version': COOKIECUTTER_REQVER},
    {'modname': "diff_match_patch",
     'package_name': "diff-match-patch",
     'features': _("Compute text file diff changes during edition"),
     'required_version': DIFF_MATCH_PATCH_REQVER},
    {'modname': "intervaltree",
     'package_name': "intervaltree",
     'features': _("Compute folding range nesting levels"),
     'required_version': INTERVALTREE_REQVER},
    {'modname': "IPython",
     'package_name': "IPython",
     'features': _("IPython interactive python environment"),
     'required_version': IPYTHON_REQVER},
    {'modname': "jedi",
     'package_name': "jedi",
     'features': _("Main backend for the Python Language Server"),
     'required_version': JEDI_REQVER},
    {'modname': "keyring",
     'package_name': "keyring",
     'features': _("Save Github credentials to report internal "
                   "errors securely"),
     'required_version': KEYRING_REQVER,
     'display': sys.platform.startswith('linux') and not PY2},
    {'modname': "nbconvert",
     'package_name': "nbconvert",
     'features': _("Manipulate Jupyter notebooks in the Editor"),
     'required_version': NBCONVERT_REQVER},
    {'modname': "numpydoc",
     'package_name': "numpydoc",
     'features': _("Improve code completion for objects that use Numpy docstrings"),
     'required_version': NUMPYDOC_REQVER},
    {'modname': "paramiko",
     'package_name': "paramiko",
     'features': _("Connect to remote kernels through SSH"),
     'required_version': PARAMIKO_REQVER,
     'display': os.name == 'nt'},
    {'modname': "parso",
     'package_name': "parso",
     'features': _("Python parser that supports error recovery and "
                   "round-trip parsing"),
     'required_version': PARSO_REQVER},
    {'modname': "pexpect",
     'package_name': "pexpect",
     'features': _("Stdio support for our language server client"),
     'required_version': PEXPECT_REQVER},
    {'modname': "pickleshare",
     'package_name': "pickleshare",
     'features': _("Cache the list of installed Python modules"),
     'required_version': PICKLESHARE_REQVER},
    {'modname': "psutil",
     'package_name': "psutil",
     'features': _("CPU and memory usage info in the status bar"),
     'required_version': PSUTIL_REQVER},
    {'modname': "pygments",
     'package_name': "pygments",
     'features': _("Syntax highlighting for a lot of file types in the Editor"),
     'required_version': PYGMENTS_REQVER},
    {'modname': "pylint",
     'package_name': "pylint",
     'features': _("Static code analysis"),
     'required_version': PYLINT_REQVER},
    {'modname': 'pyls',
     'package_name': 'python-language-server',
     'features': _("Code completion and linting for the Editor"),
     'required_version': PYLS_REQVER},
    {'modname': "xdg",
     'package_name': "pyxdg",
     'features': _("Parse desktop files on Linux"),
     'required_version': PYXDG_REQVER,
     'display': sys.platform.startswith('linux')},
    {'modname': "zmq",
     'package_name': "pyzmq",
     'features': _("Client for the language server protocol (LSP)"),
     'required_version': PYZMQ_REQVER},
    {'modname': "qdarkstyle",
     'package_name': "qdarkstyle",
     'features': _("Dark style for the entire interface"),
     'required_version': QDARKSTYLE_REQVER},
    {'modname': "qtawesome",
     'package_name': "qtawesome",
     'features': _("Icon theme based on FontAwesome and Material Design icons"),
     'required_version': QTAWESOME_REQVER},
    {'modname': "qtconsole",
     'package_name': "qtconsole",
     'features': _("Main package for the IPython console"),
     'required_version': QTCONSOLE_REQVER},
    {'modname': "qtpy",
     'package_name': "qtpy",
     'features': _("Abstraction layer for Python Qt bindings."),
     'required_version': QTPY_REQVER},
    {'modname': "rtree",
     'package_name': "rtree",
     'features': _("Fast access to code snippets regions"),
     'required_version': RTREE_REQVER,
     'display': is_anaconda()},
    {'modname': "sphinx",
     'package_name': "sphinx",
     'features': _("Show help for objects in the Editor and Consoles in a dedicated pane"),
     'required_version': SPHINX_REQVER},
    {'modname': "spyder_kernels",
     'package_name': "spyder-kernels",
     'features': _("Jupyter kernels for the Spyder console"),
     'required_version': SPYDER_KERNELS_REQVER},
    {'modname': "watchdog",
     'package_name': "watchdog",
     'features': _("Watch file changes on project directories"),
     'required_version': WATCHDOG_REQVER},
]


# Optional dependencies
DESCRIPTIONS += [
    {'modname': "cython",
     'package_name': "cython",
     'features': _("Run Cython files in the IPython Console"),
     'required_version': CYTHON_REQVER,
     'kind': OPTIONAL},
    {'modname': "matplotlib",
     'package_name': "matplotlib",
     'features': _("2D/3D plotting in the IPython console"),
     'required_version': MATPLOTLIB_REQVER,
     'kind': OPTIONAL},
    {'modname': "numpy",
     'package_name': "numpy",
     'features': _("View and edit two and three dimensional arrays in the Variable Explorer"),
     'required_version': NUMPY_REQVER,
     'kind': OPTIONAL},
    {'modname': 'pandas',
     'package_name':  'pandas',
     'features': _("View and edit DataFrames and Series in the Variable Explorer"),
     'required_version': PANDAS_REQVER,
     'kind': OPTIONAL},
    {'modname': "scipy",
     'package_name': "scipy",
     'features': _("Import Matlab workspace files in the Variable Explorer"),
     'required_version': SCIPY_REQVER,
     'kind': OPTIONAL},
    {'modname': "sympy",
     'package_name': "sympy",
     'features': _("Symbolic mathematics in the IPython Console"),
     'required_version': SYMPY_REQVER,
     'kind': OPTIONAL}
]


# =============================================================================
# Code
# =============================================================================
class Dependency(object):
    """Spyder's dependency

    version may starts with =, >=, > or < to specify the exact requirement ;
    multiple conditions may be separated by ';' (e.g. '>=0.13;<1.0')"""

    OK = 'OK'
    NOK = 'NOK'

    def __init__(self, modname, package_name, features, required_version,
                 installed_version=None, kind=MANDATORY):
        self.modname = modname
        self.package_name = package_name
        self.features = features
        self.required_version = required_version
        self.kind = kind

        if installed_version is None:
            try:
                self.installed_version = programs.get_module_version(modname)
            except Exception:
                # NOTE: Don't add any exception type here!
                # Modules can fail to import in several ways besides
                # ImportError
                self.installed_version = None
        else:
            self.installed_version = installed_version

    def check(self):
        """Check if dependency is installed"""
        if self.required_version and self.installed_version:
            return programs.is_module_installed(self.modname,
                                                self.required_version,
                                                self.installed_version)
        else:
            return True

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
        installed_version=None, kind=MANDATORY):
    """Add Spyder dependency"""
    global DEPENDENCIES
    for dependency in DEPENDENCIES:
        if dependency.modname == modname:
            raise ValueError("Dependency has already been registered: %s"\
                             % modname)
    DEPENDENCIES += [Dependency(modname, package_name, features,
                                required_version,
                                installed_version, kind)]


def check(modname):
    """Check if required dependency is installed"""
    for dependency in DEPENDENCIES:
        if dependency.modname == modname:
            return dependency.check()
    else:
        raise RuntimeError("Unkwown dependency %s" % modname)


def status(deps=DEPENDENCIES, linesep=os.linesep):
    """Return a status of dependencies."""
    maxwidth = 0
    data = []

    # Find maximum width
    for dep in deps:
        title = dep.modname
        if dep.required_version is not None:
            title += ' ' + dep.required_version

        maxwidth = max([maxwidth, len(title)])
        dep_order = {MANDATORY: '0', OPTIONAL: '1', PLUGIN: '2'}
        order_dep = {'0': MANDATORY, '1': OPTIONAL, '2': PLUGIN}
        data.append([dep_order[dep.kind], title, dep.get_installed_version()])

    # Construct text and sort by kind and name
    maxwidth += 1
    text = ""
    prev_order = '-1'
    for order, title, version in sorted(data,
                                        key=lambda x: x[0] + x[1].lower()):
        if order != prev_order:
            text += '{sep}# {name}:{sep}'.format(
                sep=linesep, name=order_dep[order].capitalize())
            prev_order = order

        text += '{title}:  {version}{linesep}'.format(
            title=title.ljust(maxwidth), version=version, linesep=linesep)

    # Remove spurious linesep when reporting deps to Github
    if not linesep == '<br>':
        text = text[:-1]

    return text


def missing_dependencies():
    """Return the status of missing dependencies (if any)"""
    missing_deps = []
    for dependency in DEPENDENCIES:
        if not dependency.check() and dependency.kind != OPTIONAL:
            missing_deps.append(dependency)

    if missing_deps:
        return status(deps=missing_deps, linesep='<br>')
    else:
        return ""


def declare_dependencies():
    for dep in DESCRIPTIONS:
        if dep.get('display', True):
            add(dep['modname'], dep['package_name'],
                dep['features'], dep['required_version'],
                kind=dep.get('kind', MANDATORY))

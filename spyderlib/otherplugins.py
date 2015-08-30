# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder third-party plugins configuration management
"""

import importlib
import sys
import traceback

# Local imports
from spyderlib.config.base import get_conf_path
from spyderlib.py3compat import PY2, PY3, PY33
from spyderlib.utils.external.path import Path

if PY2:
    import imp

INIT_PY = """# -*- coding: utf-8 -*-

# Declare as a namespace package
__import__('pkg_resources').declare_namespace(__name__)
"""


def _get_spyderplugins(plugin_path, base_namespace, plugins_namespace,
                       modnames, modlist):
    """Scan the directory `plugin_path` for plugins_namespace package and
    loads its submodules."""
    namespace_path = Path(plugin_path) / base_namespace / plugins_namespace

    if not namespace_path.exists():
        return

    for dirname in namespace_path.dirs():
        if dirname.name == "__pycache__":
            continue
        _import_plugin(dirname.name, base_namespace, plugins_namespace,
                       namespace_path, modnames, modlist)

    for name in namespace_path.files(pattern="*.py"):
        if name.name == "__init__.py":
            continue
        _import_plugin(name.namebase, base_namespace, plugins_namespace,
                       namespace_path, modnames, modlist)


class _ModuleMock():
    """ """


def _import_plugin(name, base_namespace, plugin_namespace, namespace_path,
                   modnames, modlist):
    """Import the plugin `plugins_namsepace`.`name`, add it to `modlist` and
    adds its name to `modname`."""
    module_name = "{0}.{1}.{2}".format(base_namespace, plugin_namespace, name)

    if module_name in modnames:
        return
    try:
        # First add a mock module with the LOCALEPATH attribute so that the
        # helper method can fin the locale on import
        mock = _ModuleMock()
        mock.LOCALEPATH = Path(namespace_path) / name / 'locale'
        sys.modules[module_name] = mock

        if PY33:
            loader = importlib.machinery.PathFinder.find_module(
                name, [namespace_path])
            module = loader.load_module(name)
        elif PY3:
            spec = importlib.machinery.PathFinder.find_spec(name,
                                                            [namespace_path])
            module = spec.loader.load_module(name)
        else:
            info = imp.find_module(name, [namespace_path])
            module = imp.load_module(module_name, *info)

        # Then restore the actual loaded module instead of the mock
        sys.modules[module_name] = module

        modlist.append(module)
        modnames.append(module_name)
    except Exception:
        sys.stderr.write("ERROR: 3rd party plugin import failed for "
                         "`{0}`\n".format(module_name))
        traceback.print_exc(file=sys.stderr)


def get_spyderplugins_mods(io=False):
    """Import modules from plugins package and return the list"""
    base_namespace = "spyplugins"

    if io:
        plugins_namespace = "io"
    else:
        plugins_namespace = "ui"

    namespace = '.'.join([base_namespace, plugins_namespace])

    # Import parent module
    importlib.import_module(namespace)

    # Create user directory
    user_conf_path = Path(get_conf_path())
    user_plugin_basepath = user_conf_path / base_namespace
    user_plugin_path = user_conf_path / base_namespace / plugins_namespace
    user_plugin_path.makedirs_p()
    (user_plugin_basepath / "__init__.py").write_text(INIT_PY)
    (user_plugin_path / "__init__.py").write_text(INIT_PY)

    modlist, modnames = [], []

    # The user plugins directory is given the priority when looking for modules
    for plugin_path in [user_conf_path] + sys.path:
        _get_spyderplugins(plugin_path, base_namespace, plugins_namespace,
                           modnames, modlist)
    return modlist

# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder third-party plugins configuration management
"""

import sys
import traceback
import imp

# Local imports
from spyderlib.baseconfig import get_conf_path
from spyderlib.utils.external.path import Path

INIT_PY = """# -*- coding: utf-8 -*-

# Declare as a namespace package
__import__('pkg_resources').declare_namespace(__name__)
"""

def _get_spyderplugins(plugin_path, plugins_namsepace, modnames, modlist):
    """Scan the directory `plugin_path` for plugins_namsepace package and
    loads its submodules."""
    namespace_path = Path(plugin_path) / plugins_namsepace
    if not namespace_path.exists():
        return
    for dirname in namespace_path.dirs():
        if dirname.name == "__pycache__":
            continue
        _import_plugin(dirname.name, plugins_namsepace, namespace_path,
                       modnames, modlist)
    for name in namespace_path.files(pattern="*.py"):
        if name.name == "__init__.py":
            continue
        _import_plugin(name.namebase, plugins_namsepace, namespace_path,
                       modnames, modlist)


def _import_plugin(name, plugins_namsepace, namespace_path, modnames, modlist):
    """Import the plugin `plugins_namsepace`.`name`, add it to `modlist` and
    adds its name to `modname`."""
    submodule_name = "%s.%s" % (plugins_namsepace, name)
    if submodule_name in modnames:
        return
    try:
        info = imp.find_module(name, [namespace_path])
        submodule = imp.load_module(submodule_name, *info)
        modlist.append(submodule)
        modnames.append(submodule_name)
    except Exception:
        sys.stderr.write(
            "ERROR: 3rd party plugin import failed for `%s`\n"
            % submodule_name)
        traceback.print_exc(file=sys.stderr)


def get_spyderplugins_mods(io=False):
    """Import modules from plugins package and return the list"""
    if io:
        plugins_namsepace = "spyderioplugins"
    else:
        plugins_namsepace = "spyderplugins"
    # Import parent module
    __import__(plugins_namsepace)

    # Create user directory
    user_conf_path = Path(get_conf_path())
    user_plugin_path = user_conf_path / plugins_namsepace
    user_plugin_path.makedirs_p()
    (user_plugin_path / "__init__.py").write_text(INIT_PY)

    modlist = []
    modnames = []
    for directory in [user_conf_path] + sys.path:
        _get_spyderplugins(directory, plugins_namsepace, modnames, modlist)
    return modlist

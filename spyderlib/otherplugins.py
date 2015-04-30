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

# Local imports
from spyderlib.utils import programs
from spyderlib.baseconfig import get_conf_path
from spyderlib.utils.external.path import path as Path


def _get_spyderplugins(plugin_path):
    """Scan directory of `spyderplugins` package and
    return the list of module names matching *prefix*"""
    plist = []
    for dirname in plugin_path.dirs():
        if not (dirname / "__init__.py").isfile():
            continue
        plist.append(dirname.name)
    for name in plugin_path.files(pattern="*.py"):
        plist.append(name.namebase)
    return plist


def _import_plugin(name, modlist):
    """Import the plugin `modname` and add it to `modlist`"""
    try:
        __import__(name)
        modlist.append(sys.modules[name])
    except Exception:
        sys.stderr.write(
            "ERROR: 3rd party plugin import failed for `%s`\n" % name)
        traceback.print_exc(file=sys.stderr)


def get_spyderplugins_mods(io=False):
    """Import modules from plugins package and return the list"""

    if io:
        user_plugin_namsepace = "userioplugins"
        plugin_namsepace = "spyderioplugins"
    else:
        user_plugin_namsepace = "userplugins"
        plugin_namsepace = "spyderplugins"

    modlist = []

    # Load user plugins
    user_plugin_path = Path(get_conf_path(user_plugin_namsepace))
    user_plugin_path.makedirs_p()
    user_plugins = _get_spyderplugins(user_plugin_path)
    sys.path.insert(0, user_plugin_path)
    try:
        for modname in user_plugins:
            _import_plugin(modname, modlist)
    finally:
        sys.path.remove(user_plugin_path)

    # Load system plugins not already loaded
    if programs.is_module_installed(plugin_namsepace):
        plugin_module = __import__(plugin_namsepace)
        # list() is needed since python 3.3
        plugin_path = Path(list(plugin_module.__path__)[0]).abspath()
        # py2exe/cx_Freeze distribution: ignoring extra plugins
        if plugin_path.isdir():
            for modname in _get_spyderplugins(plugin_path):
                if modname not in user_plugins:
                    name = '%s.%s' % (plugin_namsepace, modname)
                    _import_plugin(name, modlist)

    return modlist

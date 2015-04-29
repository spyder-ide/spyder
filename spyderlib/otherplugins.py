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

# Calculate path to `spyderplugins` package, where Spyder looks for all 3rd
# party plugin modules
PLUGIN_PATH = None
if programs.is_module_installed("spyderplugins"):
    import spyderplugins
    PLUGIN_PATH = Path(spyderplugins.__path__[0]).abspath()
    if not PLUGIN_PATH.isdir():
        # py2exe/cx_Freeze distribution: ignoring extra plugins
        PLUGIN_PATH = None

USERPLUGIN_PATH = Path(get_conf_path("userplugins"))
USERPLUGIN_PATH.makedirs_p()
sys.path.append(USERPLUGIN_PATH)


def _get_spyderplugins(plugin_path, prefix):
    """Scan directory of `spyderplugins` package and
    return the list of module names matching *prefix*"""
    plist = []
    if PLUGIN_PATH is not None:
        for dirname in plugin_path.dirs(pattern=prefix + "*"):
            if not (dirname / "__init__.py").isfile():
                continue
            plist.append(dirname.name)
        for name in plugin_path.files(pattern=prefix + "*.py"):
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


def get_spyderplugins_mods(prefix):
    """Import modules that match *prefix* from
    `spyderplugins` package and return the list"""
    modlist = []

    # Load user plugins
    user_plugins = _get_spyderplugins(USERPLUGIN_PATH, prefix)
    sys.path.insert(0, USERPLUGIN_PATH)
    try:
        for modname in user_plugins:
            _import_plugin(modname, modlist)
    finally:
        sys.path.remove(USERPLUGIN_PATH)

    # Load system plugins not already loaded
    for modname in _get_spyderplugins(PLUGIN_PATH, prefix):
        if modname not in user_plugins:
            name = 'spyderplugins.%s' % modname
            _import_plugin(name, modlist)
    return modlist

# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder third-party plugins configuration management
"""

import os
import os.path as osp
import sys
import traceback

# Local imports
from spyderlib.utils import programs


# Calculate path to `spyderplugins` package, where Spyder looks for all 3rd
# party plugin modules
PLUGIN_PATH = None
if programs.is_module_installed("spyderplugins"):
    import spyderplugins
    PLUGIN_PATH = osp.abspath(spyderplugins.__path__[0])
    if not osp.isdir(PLUGIN_PATH):
        # py2exe/cx_Freeze distribution: ignoring extra plugins
        PLUGIN_PATH = None


def get_spyderplugins(prefix):
    """Scan directory of `spyderplugins` package and
    return the list of module names matching *prefix*"""
    plist = []
    if PLUGIN_PATH is not None:
        for name in os.listdir(PLUGIN_PATH):
            if not name.startswith(prefix):
                continue
            if osp.isdir(osp.join(PLUGIN_PATH, name)):
                if not osp.isfile(osp.join(PLUGIN_PATH, name, "__init__.py")):
                    continue
                modname = name
            else:
                modname, ext = osp.splitext(name)
                if ext != ".py":
                    continue
            plist.append(modname)
    return plist


def get_spyderplugins_mods(prefix):
    """Import modules that match *prefix* from
    `spyderplugins` package and return the list"""
    modlist = []
    for modname in get_spyderplugins(prefix):
        name = 'spyderplugins.%s' % modname
        try:
            __import__(name)
            modlist.append(sys.modules[name])
        except Exception:
            sys.stderr.write(
                "ERROR: 3rd party plugin import failed for `%s`\n" % modname)
            traceback.print_exc(file=sys.stderr)
    return modlist

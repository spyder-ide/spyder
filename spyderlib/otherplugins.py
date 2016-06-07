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
from spyderlib.config.base import get_conf_path
from spyderlib.py3compat import PY2

if PY2:
    import imp
else:
    import importlib


PLUGIN_PREFIX = "spyder_"
IO_PREFIX = PLUGIN_PREFIX + "io_"


def get_spyderplugins_mods(io=False):
    """Import modules from plugins package and return the list"""
    # Create user directory
    user_conf_path = get_conf_path()
    user_plugin_path = osp.join(user_conf_path, "spyplugins")
    create_userplugins_files(user_plugin_path)

    modlist, modnames = [], []

    # The user plugins directory is given the priority when looking for modules
    for plugin_path in [user_conf_path] + sys.path:
        _get_spyderplugins(plugin_path, io, modnames, modlist)
    return modlist


def _get_spyderplugins(plugin_path, is_io, modnames, modlist):
    """Scan the directory `plugin_path` for plugins_namespace package and
    loads its submodules."""
    if not osp.isdir(plugin_path):
        return

    for name in os.listdir(plugin_path):
        if is_io and not name.startswith(IO_PREFIX):
            continue
        # Check if it's a spyder plugin
        if not name.startswith(PLUGIN_PREFIX) or name.startswith(IO_PREFIX):
            continue

        # Import the plugin
        _import_plugin(name, plugin_path, modnames, modlist)


class _ModuleMock():
    """This mock module is added to sys.modules on plugin load to add the
    location of the LOCALEDATA so that the module loads succesfully.
    Once loaded the module is replaced by the actual loaded module object.
    """
    pass


def _import_plugin(module_name, plugin_path, modnames, modlist):
    """Import the plugin `plugins_namsepace`.`name`, add it to `modlist` and
    adds its name to `modnames`."""
    if module_name in modnames:
        return
    try:
        # First add a mock module with the LOCALEPATH attribute so that the
        # helper method can find the locale on import
        mock = _ModuleMock()
        mock.LOCALEPATH = osp.join(plugin_path, 'locale')
        sys.modules[module_name] = mock
        module = None

        if PY2:
            info = imp.find_module(module_name, [plugin_path])
            if info:
                module = imp.load_module(module_name, *info)
        elif sys.version_info[0:2] <= (3, 3):
            loader = importlib.machinery.PathFinder.find_module(
                module_name,
                [plugin_path])
            if loader:
                module = loader.load_module(module_name)
        else:
            spec = importlib.machinery.PathFinder.find_spec(
                module_name,
                [plugin_path])
            if spec:
                module = spec.loader.load_module(module_name)

        # Then restore the actual loaded module instead of the mock
        if module:
            sys.modules[module_name] = module
            modlist.append(module)
            modnames.append(module_name)
    except Exception:
        sys.stderr.write("ERROR: 3rd party plugin import failed for "
                         "`{0}`\n".format(module_name))
        traceback.print_exc(file=sys.stderr)


def create_userplugins_files(path):
    """
    Create userplugins namespace dirs and files if not present in .spyder* dir
    """
    if not osp.isdir(path):
        os.makedirs(path)

    init_file = "__init__.py"
    init_file_content = """# -*- coding: utf-8 -*-
'''
'spyplugins' makes uses of namespace packages to keep different plugins
organized in the sitepackages directory and in the user directory.

Spyder plugins can be of 'io' type or 'ui' type. Each type also makes use
of namespace packages.

For more information on namespace packages visit:
- https://www.python.org/dev/peps/pep-0382/
- https://www.python.org/dev/peps/pep-0420/
'''
"""
    data = ""
    new_path = osp.join(path, init_file)
    if osp.isfile(new_path):
        with open(new_path, "r") as f:
            data = f.read()

    if not (osp.isfile(new_path) and data == init_file_content):
        with open(new_path, "w") as f:
            f.write(init_file_content)

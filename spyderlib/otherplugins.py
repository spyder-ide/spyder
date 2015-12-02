# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder third-party plugins configuration management
"""

import importlib
import os
import os.path as osp
import sys
import traceback

# Local imports
from spyderlib.config.base import get_conf_path
from spyderlib.py3compat import PY2, PY3, PY33

if PY2:
    import imp


def _get_spyderplugins(plugin_path, base_namespace, plugins_namespace,
                       modnames, modlist):
    """Scan the directory `plugin_path` for plugins_namespace package and
    loads its submodules."""
    namespace_path = osp.join(plugin_path, base_namespace, plugins_namespace)

    if not osp.exists(namespace_path):
        return

    dirs = []
    for d in os.listdir(namespace_path):
        path = osp.join(namespace_path, d)
        if osp.isdir(path):
            dirs.append(path)
            
    for dirname in dirs:
        name = osp.basename(dirname)
        if name == "__pycache__":
            continue
        _import_plugin(name, base_namespace, plugins_namespace,
                       namespace_path, modnames, modlist)


class _ModuleMock():
    """This mock module is added to sys.modules on plugin load to add the
    location of the LOCALEDATA so that the module loads succesfully.
    Once loaded the module is replaced by the actual loaded module object.
    """
    pass


def _import_plugin(name, base_namespace, plugin_namespace, namespace_path,
                   modnames, modlist):
    """Import the plugin `plugins_namsepace`.`name`, add it to `modlist` and
    adds its name to `modnames`."""
    module_name = "{0}.{1}.{2}".format(base_namespace, plugin_namespace, name)

    if module_name in modnames:
        return
    try:
        # First add a mock module with the LOCALEPATH attribute so that the
        # helper method can find the locale on import
        mock = _ModuleMock()
        mock.LOCALEPATH = osp.join(namespace_path, name, 'locale')
        sys.modules[module_name] = mock
        module = None
        if PY33:
            loader = importlib.machinery.PathFinder.find_module(
                name, [namespace_path])
            if loader:
                module = loader.load_module(name)
        elif PY3:
            spec = importlib.machinery.PathFinder.find_spec(name,
                                                            [namespace_path])
            if spec:
                module = spec.loader.load_module(name)
        else:
            info = imp.find_module(name, [namespace_path])
            if info:
                module = imp.load_module(module_name, *info)

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

# Declare as a namespace package
__import__('pkg_resources').declare_namespace(__name__)
"""
    data = ""
    new_path = osp.join(path, init_file)
    if osp.isfile(new_path):
        with open(new_path, "r") as f:
            data = f.read()

    if not (osp.isfile(new_path) and data == init_file_content):
        with open(new_path, "w") as f:
            f.write(init_file_content)


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
    user_conf_path = get_conf_path()
    user_plugin_basepath = osp.join(user_conf_path, base_namespace)
    user_plugin_path = osp.join(user_conf_path, base_namespace,
                                plugins_namespace)

    create_userplugins_files(user_plugin_basepath)
    create_userplugins_files(user_plugin_path)

    modlist, modnames = [], []

    # The user plugins directory is given the priority when looking for modules
    for plugin_path in [user_conf_path] + sys.path:
        _get_spyderplugins(plugin_path, base_namespace, plugins_namespace,
                           modnames, modlist)
    return modlist

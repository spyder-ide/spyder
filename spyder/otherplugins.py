# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder third-party plugins configuration management.
"""

# Standard library imports
import importlib
import logging
import os
import os.path as osp
import sys
import traceback

# Local imports
from spyder.config.base import get_conf_path
from spyder.py3compat import to_text_string


# Constants
logger = logging.getLogger(__name__)
USER_PLUGIN_DIR = "plugins"
PLUGIN_PREFIX = "spyder_"
IO_PREFIX = PLUGIN_PREFIX + "io_"


def get_spyderplugins_mods(io=False):
    """Import modules from plugins package and return the list"""
    # Create user directory
    user_plugin_path = osp.join(get_conf_path(), USER_PLUGIN_DIR)
    if not osp.isdir(user_plugin_path):
        os.makedirs(user_plugin_path)

    modlist, modnames = [], []

    # The user plugins directory is given the priority when looking for modules
    for plugin_path in [user_plugin_path] + sys.path:
        _get_spyderplugins(plugin_path, io, modnames, modlist)
    return modlist


def _get_spyderplugins(plugin_path, is_io, modnames, modlist):
    """Scan the directory `plugin_path` for plugin packages and loads them."""
    if not osp.isdir(plugin_path):
        return

    for name in os.listdir(plugin_path):
        # This is needed in order to register the spyder_io_hdf5 plugin.
        # See spyder-ide/spyder#4487.
        # Is this a Spyder plugin?
        if not name.startswith(PLUGIN_PREFIX):
            continue

        # Ensure right type of plugin
        if is_io and not name.startswith(IO_PREFIX):
            continue

        # Skip names that end in certain suffixes
        forbidden_suffixes = ['dist-info', 'egg.info', 'egg-info', 'egg-link',
                              'kernels']
        if any([name.endswith(s) for s in forbidden_suffixes]):
            continue

        # Import the plugin
        _import_plugin(name, plugin_path, modnames, modlist)


def _import_plugin(module_name, plugin_path, modnames, modlist):
    """Import the plugin `module_name` from `plugin_path`, add it to `modlist`
    and adds its name to `modnames`.
    """
    if module_name in modnames:
        return
    try:
        # First add a mock module with the LOCALEPATH attribute so that the
        # helper method can find the locale on import
        mock = _ModuleMock()
        mock.LOCALEPATH = osp.join(plugin_path, module_name, 'locale')
        sys.modules[module_name] = mock

        if osp.isdir(osp.join(plugin_path, module_name)):
            module = _import_module_from_path(module_name, plugin_path)
        else:
            module = None

        # Then restore the actual loaded module instead of the mock
        if module and getattr(module, 'PLUGIN_CLASS', False):
            sys.modules[module_name] = module
            modlist.append(module)
            modnames.append(module_name)
    except Exception as e:
        sys.stderr.write("ERROR: 3rd party plugin import failed for "
                         "`{0}`\n".format(module_name))
        traceback.print_exc(file=sys.stderr)


def _import_module_from_path(module_name, plugin_path):
    """Imports `module_name` from `plugin_path`.

    Return None if no module is found.
    """
    module = None
    try:
        spec = importlib.machinery.PathFinder.find_spec(
            module_name,
            [plugin_path])

        if spec:
            module = spec.loader.load_module(module_name)
    except Exception as err:
        debug_message = ("plugin: '{module_name}' load failed with `{err}`"
                         "").format(module_name=module_name,
                                    err=to_text_string(err))
        logger.debug(debug_message)

    return module


class _ModuleMock():
    """This mock module is added to sys.modules on plugin load to add the
    location of the LOCALEDATA so that the module loads succesfully.
    Once loaded the module is replaced by the actual loaded module object.
    """
    pass

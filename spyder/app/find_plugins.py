# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
Plugin dependency solver.
"""

import ast
import importlib
import logging
import os
import traceback

import pkg_resources

from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import (
    SpyderDockablePlugin, SpyderPluginWidget, Plugins)
from spyder.api.utils import get_class_values
from spyder.config.base import (
    DEV, STDERR, running_in_ci, running_under_pytest)


logger = logging.getLogger(__name__)


def find_internal_plugins():
    """
    Find internal plugins based on setup.py entry points.

    In DEV mode we parse the `setup.py` file directly.
    """
    internal_plugins = {}

    # If DEV, look for entry points in setup.py file for internal plugins
    # and then look on the system for the rest
    HERE = os.path.abspath(os.path.dirname(__file__))
    base_path = os.path.dirname(os.path.dirname(HERE))
    setup_path = os.path.join(base_path, "setup.py")

    if (DEV or running_under_pytest()) and not running_in_ci():
        if not os.path.isfile(setup_path):
            raise Exception(
                'No "setup.py" file found and running in DEV mode!')

        with open(setup_path, "r") as fh:
            lines = fh.read().split("\n")

        start = None
        end = None
        for idx, line in enumerate(lines):
            if line.startswith("spyder_plugins_entry_points"):
                start = idx + 1
                continue

            if start is not None:
                if line.startswith("]"):
                    end = idx + 1
                    break

        entry_points_list = "[" + "\n".join(lines[start:end])
        spyder_plugin_entry_points = ast.literal_eval(entry_points_list)
        for entry_point in spyder_plugin_entry_points:
            try:
                name, module = entry_point.split(" = ")
                name = name.strip()
                module = module.strip()
                module, class_name = module.split(":")
            except Exception:
                logger.error(
                    '"setup.py" entry point "{entry_point}" is malformed!'
                    "".format(entry_point=entry_point)
                )

            try:
                mod = importlib.import_module(module)
                internal_plugins[name] = getattr(mod, class_name, None)
            except (ModuleNotFoundError, ImportError) as e:
                raise e
    else:
        entry_points = list(pkg_resources.iter_entry_points("spyder.plugins"))
        internal_names = get_class_values(Plugins)

        for entry_point in entry_points:
            name = entry_point.name
            if name not in internal_names:
                continue

            class_name = entry_point.attrs[0]
            mod = importlib.import_module(entry_point.module_name)
            plugin_class = getattr(mod, class_name, None)
            internal_plugins[name] = plugin_class

        # FIXME: This shouldn't be necessary but it's just to be sure
        # plugins are sorted in alphabetical order. We need to remove it
        # in a later version.
        internal_plugins = {
            key: value for key, value in sorted(internal_plugins.items())
        }

    return internal_plugins


def find_external_plugins():
    """
    Find available external plugins based on setuptools entry points.
    """
    internal_names = get_class_values(Plugins)
    plugins = list(pkg_resources.iter_entry_points("spyder.plugins"))
    external_plugins = {}

    for entry_point in plugins:
        name = entry_point.name
        if name not in internal_names:
            try:
                class_name = entry_point.attrs[0]
                mod = importlib.import_module(entry_point.module_name)
                plugin_class = getattr(mod, class_name, None)

                # To display in dependencies dialog.
                # Skipped if running under test (to load boilerplate plugin)
                if not running_under_pytest():
                    plugin_class._spyder_module_name = entry_point.module_name
                    plugin_class._spyder_package_name = (
                        entry_point.dist.project_name)
                    plugin_class._spyder_version = entry_point.dist.version

                external_plugins[name] = plugin_class
                if name != plugin_class.NAME:
                    raise SpyderAPIError(
                        "Entry point name '{0}' and plugin.NAME '{1}' "
                        "do not match!".format(name, plugin_class.NAME)
                    )
            except (ModuleNotFoundError, ImportError) as error:
                print("%s: %s" % (name, str(error)), file=STDERR)
                traceback.print_exc(file=STDERR)

    return external_plugins

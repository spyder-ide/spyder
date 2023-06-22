# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for config/manager.py."""

# Standard library imports
import configparser
import os
import os.path as osp
import shutil
import tempfile

# Third party imports
import pytest

# Local imports
from spyder.config.base import get_conf_path, get_conf_paths
from spyder.config.manager import ConfigurationManager
from spyder.plugins.console.plugin import Console


def clear_site_config():
    """Delete all test site config folders."""
    for path in get_conf_paths():
        shutil.rmtree(path)


def test_site_config_load():
    """
    Test that the site/system config preferences are loaded with correct
    precedence.
    """
    clear_site_config()

    for i, path in enumerate(reversed(get_conf_paths())):
        exp_value = 100*(1 + i)
        content = '[main]\nmemory_usage/timeout = ' + str(exp_value) + '\n'

        conf_fpath = os.path.join(path, 'spyder.ini')
        with open(conf_fpath, 'w') as fh:
            fh.write(content)

        config = ConfigurationManager()
        config.reset_to_defaults()
        value = config.get('main', 'memory_usage/timeout')

        print(path, value, exp_value)
        assert value == exp_value

    clear_site_config()


def test_external_plugin_config(qtbot):
    """
    Test that config for external plugins is saved as expected.

    This includes a regression for part two (the shortcuts conflict) of
    issue spyder-ide/spyder#11132
    """
    clear_site_config()

    # Emulate an old Spyder 3 configuration
    spy3_config = """
[main]
version = 1.0.0

[shortcuts]
foo/bar = Alt+1

[ipython_console]
startup/run_lines =
"""
    conf_fpath = get_conf_path('spyder.ini')
    with open(conf_fpath, 'w') as f:
        f.write(spy3_config)

    # Create config manager
    manager = ConfigurationManager()

    # Set default options for the internal console
    Console.CONF_FILE = True
    defaults = [
        ('internal_console',
         {
            'max_line_count': 300,
            'working_dir_history': 30,
            'working_dir_adjusttocontents': False,
            'wrap': True,
            'codecompletion/auto': False,
            'external_editor/path': 'SciTE',
            'external_editor/gotoline': '-goto:'
         }
        ),
    ]
    Console.CONF_DEFAULTS = defaults

    # Register console plugin config
    manager.register_plugin(Console)

    # Assert the dummy shortcut is not present in the plugin config
    with pytest.raises(configparser.NoSectionError):
        manager.get_shortcut('foo', 'bar', plugin_name='internal_console')

    # Change an option in the console
    console = Console(None, configuration=manager)
    console.set_conf('max_line_count', 600)

    # Read config filew directly
    user_path = manager.get_user_config_path()
    with open(osp.join(user_path, 'spyder.ini'), 'r') as f:
        user_contents = f.read()

    plugin_path = manager.get_plugin_config_path('internal_console')
    with open(osp.join(plugin_path, 'spyder.ini'), 'r') as f:
        plugin_contents = f.read()

    # Assert that the change was written to the right config file
    assert 'max_line_count = 600' not in user_contents
    assert 'max_line_count = 600' in plugin_contents

    shutil.rmtree(plugin_path)
    Console.CONF_FILE = False
    clear_site_config()


if __name__ == "__main__":
    pytest.main()

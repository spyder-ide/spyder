# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for config/manager.py."""

# Standard library imports
import os
import shutil
import tempfile

# Third party imports
import pytest

# Local imports
from spyder.config.base import get_conf_paths
from spyder.config.manager import ConfigurationManager


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


if __name__ == "__main__":
    pytest.main()

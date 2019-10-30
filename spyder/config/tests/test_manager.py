# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for config/manager.py."""

# Standard library imports
import os
import tempfile

# Third party imports
import pytest

# Local imports
import spyder.config.base


def get_config_paths_mock():
    search_paths = []
    for i in range(3):
        path = tempfile.mkdtemp(suffix='-'+str(i))
        search_paths.append(path)
    return search_paths


def test_site_config_load(mocker):
    """
    Test that the site/system config preferences are loaded with correct
    precedence.
    """
    mocker.patch.object(spyder.config.base, 'get_conf_paths',
                        return_value=get_config_paths_mock())

    print('path, value, expected value')
    for i, path in enumerate(reversed(spyder.config.base.get_conf_paths())):
        exp_value = 100*(1 + i)
        content = '[main]\nmemory_usage/timeout = ' + str(exp_value) + '\n'

        with open(os.path.join(path, 'spyder.ini'), 'w') as fh:
            fh.write(content)

        from spyder.config.manager import ConfigurationManager
        config = ConfigurationManager()
        config.reset_to_defaults()
        value = config.get('main', 'memory_usage/timeout')

        print(path, value, exp_value)

        assert value == exp_value


if __name__ == "__main__":
    pytest.main()

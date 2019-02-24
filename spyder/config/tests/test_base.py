# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for the spyder.config.base module.
"""

# Standard library imports
import os.path as osp
try:
    from importlib import reload
except ImportError:  # A builtin on Python 2
    pass

# Third party imports
import pytest

# Local imports
import spyder.config.base


# ============================================================================
# ---- Tests
# ============================================================================
@pytest.mark.parametrize('version_input, expected_result', [
    ('3.3.0', True), ('2', True), (('0', '5'), True), ('4.0.0b1', False),
    ('3.3.2.dev0', False), ('beta', False), (('2', '0', 'alpha'), False)])
def test_is_stable_version(version_input, expected_result):
    """Test that stable and non-stable versions are recognized correctly."""
    actual_result = spyder.config.base.is_stable_version(version_input)
    assert actual_result == expected_result


@pytest.mark.parametrize('use_dev_config_dir', [True, False])
def test_get_conf_path(monkeypatch, use_dev_config_dir):
    """Test that the config dir path is set under dev and release builds."""
    monkeypatch.setenv('SPYDER_USE_DEV_CONFIG_DIR', str(use_dev_config_dir))
    reload(spyder.config.base)
    conf_path = spyder.config.base.get_conf_path()
    assert conf_path
    assert ((osp.basename(conf_path).split('-')[-1] == 'dev')
            == use_dev_config_dir)
    assert osp.isdir(conf_path)
    monkeypatch.undo()
    reload(spyder.config.base)


if __name__ == '__main__':
    pytest.main()

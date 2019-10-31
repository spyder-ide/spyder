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
import os
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
def test_is_stable_version():
    """Test that stable and non-stable versions are recognized correctly."""
    for stable_version in ['3.3.0', '2', ('0', '5')]:
        assert spyder.config.base.is_stable_version(stable_version)
    for not_stable_version in ['4.0.0b1', '3.3.2.dev0',
                               'beta', ('2', '0', 'alpha')]:
        assert not spyder.config.base.is_stable_version(not_stable_version)


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

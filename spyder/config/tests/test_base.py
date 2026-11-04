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
from importlib import reload
import os
import os.path as osp
from pathlib import Path
import shutil
import sys


# Third party imports
import pytest
from spyder_kernels.utils.pythonenv import is_conda_env

# Local imports
import spyder.config.base
from spyder.utils.conda import get_list_conda_envs


# ============================================================================
# ---- Helpers
# ============================================================================
def use_default_conf_dir(monkeypatch, home):
    """Make get_conf_path use its default location under `home`."""
    monkeypatch.setattr(spyder.config.base, 'running_under_pytest',
                        lambda: False)
    monkeypatch.setattr(spyder.config.base, 'get_safe_mode', lambda: False)
    monkeypatch.setattr(spyder.config.base, 'get_home_dir', lambda: home)
    monkeypatch.delenv('SPYDER_CONFDIR', raising=False)
    monkeypatch.setenv('XDG_CONFIG_HOME', osp.join(home, '.config'))


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
    monkeypatch.setenv('SPYDER_PYTEST', '')
    reload(spyder.config.base)
    conf_path = spyder.config.base.get_conf_path()
    assert conf_path
    assert ((osp.basename(conf_path).split('-')[-1] == 'dev')
            == use_dev_config_dir)
    assert osp.isdir(conf_path)
    monkeypatch.undo()
    reload(spyder.config.base)


def test_get_conf_path_concurrent_creation(tmp_path, monkeypatch,
                                           racing_mkdir):
    """
    Test that get_conf_path doesn't fail if another Spyder process creates
    the config dir at the same time.

    This is a regression test for spyder-ide/spyder#26494
    """
    # Default location, created with os.mkdir
    home = str(tmp_path)
    use_default_conf_dir(monkeypatch, home)
    conf_path = spyder.config.base.get_conf_path()
    assert osp.isdir(conf_path)
    assert conf_path in racing_mkdir

    # Clean location (tests and safe mode), created with os.makedirs
    clean_dir = str(tmp_path / 'clean' / 'conf')
    monkeypatch.setattr(spyder.config.base, 'running_under_pytest',
                        lambda: True)
    monkeypatch.setattr(spyder.config.base, 'get_clean_conf_dir',
                        lambda: clean_dir)
    assert spyder.config.base.get_conf_path() == clean_dir
    assert clean_dir in racing_mkdir


@pytest.mark.skipif(
    sys.platform.startswith('linux'),
    reason="The parent dir ($XDG_CONFIG_HOME) is always created on Linux"
)
def test_get_conf_path_default_dir_missing_parent(tmp_path, monkeypatch):
    """
    Test that get_conf_path doesn't create missing parent dirs for the
    default location.
    """
    use_default_conf_dir(monkeypatch, str(tmp_path / 'missing'))
    with pytest.raises(FileNotFoundError):
        spyder.config.base.get_conf_path()


def test_get_conf_path_default_dir_is_file(tmp_path, monkeypatch):
    """
    Test that get_conf_path fails for the default location if there's a file
    in its place.
    """
    use_default_conf_dir(monkeypatch, str(tmp_path))
    subfolder = spyder.config.base.get_conf_subfolder()
    if sys.platform.startswith('linux'):
        os.makedirs(tmp_path / '.config')
        (tmp_path / '.config' / subfolder).touch()
    else:
        (tmp_path / subfolder).touch()

    with pytest.raises(FileExistsError):
        spyder.config.base.get_conf_path()


def test_get_conf_paths_concurrent_creation(tmp_path, monkeypatch,
                                            racing_mkdir):
    """
    Test that get_conf_paths doesn't fail if another process creates the test
    site config dirs at the same time.
    """
    monkeypatch.setattr(spyder.config.base.tempfile, 'gettempdir',
                        lambda: str(tmp_path))
    paths = spyder.config.base.get_conf_paths()
    assert len(paths) == 3
    assert all(path in racing_mkdir for path in paths)


@pytest.mark.skipif(
    not spyder.config.base.running_in_ci(), reason="Only works on CIs"
)
@pytest.mark.skipif(
    not is_conda_env(sys.prefix), reason='Only works with Anaconda'
)
def test_is_conda_based_app():
    """Test that is_conda_based_app is working as expected."""
    # Get conda env to use
    pyexec = get_list_conda_envs()['Conda: jedi-test-env'][0]

    # Get env's root
    env_root = (
        Path(pyexec).parents[0] if os.name == "nt" else Path(pyexec).parents[1]
    )

    # Create dir and file necessary to detect the app
    menu_dir = env_root / "Menu"
    menu_dir.mkdir(exist_ok=True)
    (menu_dir / "conda-based-app").touch()

    # Check the env is not detected as belonging to the app because it's not
    # named spyder-runtime.
    assert not spyder.config.base.is_conda_based_app(pyexec=pyexec)

    # Remove added dir
    shutil.rmtree(menu_dir, ignore_errors=True)


if __name__ == '__main__':
    pytest.main()

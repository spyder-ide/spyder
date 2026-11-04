# -*- coding: utf-8 -*-
#
# Copyright (c) 2009- Spyder Project Contributors
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the `spyder.config`."""

# Standard library imports
import os

# Third party imports
import pytest

# Local imports
from spyder.config.base import get_conf_path
from spyder.config.user import DefaultsConfig, SpyderUserConfig, UserConfig


@pytest.fixture
def defaultconfig(tmpdir, request):
    name = 'defaults-test'
    path = str(tmpdir)
    default_kwargs = {'name': name, 'path': path}

    param = getattr(request, 'param', None)
    if param:
        modified_kwargs = request.param[0]
        kwargs = default_kwargs.copy().update(modified_kwargs)
    else:
        kwargs = default_kwargs

    return DefaultsConfig(**kwargs)


@pytest.fixture
def userconfig(tmpdir, request):
    ini_contents = '[main]\nversion = 1.0.0\n\n'
    ini_contents += "[section]\noption = value\n\n"

    name = 'spyder-test'
    path = str(tmpdir)
    default_kwargs = {
        'name': name,
        'path': path,
        'defaults': {},
        'load': True,
        'version': '1.0.0',
        'backup': False,
        'raw_mode': True,
        'remove_obsolete': False,
    }

    param = getattr(request, 'param', None)
    if param:
        modified_kwargs = request.param[0]
        kwargs = default_kwargs.copy().update(modified_kwargs)
    else:
        kwargs = default_kwargs

    inifile = tmpdir.join('{}.ini'.format(name))
    inifile.write(ini_contents)

    return UserConfig(**kwargs)


@pytest.fixture
def spyderconfig(tmpdir, request):
    ini_contents = '[main]\nversion = 1.0.0\n\n'
    ini_contents += """[ipython_console]
startup/run_lines = value1,value2

"""

    name = 'spyder-test'
    path = str(tmpdir)
    default_kwargs = {
        'name': name,
        'path': path,
        'defaults': {},
        'load': True,
        'version': '1.0.0',
        'backup': False,
        'raw_mode': True,
        'remove_obsolete': False,
    }

    param = getattr(request, 'param', None)
    if param:
        modified_kwargs = param[0]
        kwargs = default_kwargs.copy()
        kwargs.update(modified_kwargs)
    else:
        kwargs = default_kwargs

    inifile = tmpdir.join('{}.ini'.format(name))
    inifile.write(ini_contents)

    return SpyderUserConfig(**kwargs)


@pytest.fixture
def spyderconfig_patches_42(tmpdir):
    ini_contents = '[main]\nversion = 42.0.0\n\n'
    ini_contents += '[ipython_console]\nstartup/run_lines = value1,value2'

    name = 'spyder'
    inifile = tmpdir.join('{}.ini'.format(name))
    inifile.write(ini_contents + '\n\n')

    return SpyderUserConfig(name=name, path=str(tmpdir), defaults={},
                            load=True, version='43.0.0', backup=False,
                            raw_mode=True, remove_obsolete=False)


@pytest.fixture
def spyderconfig_patches_45(tmpdir):
    ini_contents = '[main]\nversion = 45.0.0\n\n'
    ini_contents += '[ipython_console]\nstartup/run_lines = value1,value2'

    name = 'spyder'
    inifile = tmpdir.join('{}.ini'.format(name))
    inifile.write(ini_contents + '\n\n')

    return SpyderUserConfig(name=name, path=str(tmpdir), defaults={},
                            load=True, version='46.0.0', backup=False,
                            raw_mode=True, remove_obsolete=False)


@pytest.fixture
def spyderconfig_previous(tmpdir, mocker):
    ini_contents = '[main]\nversion = 50.0.0\n\n'
    ini_contents += "[section]\noption = value"

    name = 'spyder'
    path = str(tmpdir)

    def temp(*args, **kwargs):
        return path

    mocker.patch('spyder.config.base', 'get_conf_path')
    inifile = tmpdir.join('{}.ini'.format(name))
    os.makedirs(str(tmpdir.join('app', 'config')))
    inifile2 = tmpdir.join('app', 'config', '{}.ini'.format(name))
    inifile.write(ini_contents + '\n\n')
    inifile2.write(ini_contents + '\n\n')

    return SpyderUserConfig(name=name, path=path, defaults={}, load=True,
                            version='50.0.0', backup=False, raw_mode=True,
                            remove_obsolete=False)


@pytest.fixture
def racing_mkdir(tmp_path, monkeypatch):
    """
    Simulate another Spyder process creating folders at the same time.

    Every folder this test tries to create under `tmp_path` is created first
    by a "concurrent process", i.e. right after the caller checked that it
    didn't exist and right before it creates it.

    Returns
    -------
    list of str
        Absolute paths of the folders the concurrent process created.
    """
    real_mkdir = os.mkdir
    root = str(tmp_path)
    created = []

    def mkdir(path, *args, **kwargs):
        abs_path = os.path.abspath(os.fsdecode(path))
        try:
            in_root = os.path.commonpath([root, abs_path]) == root
        except ValueError:
            # Paths on different drives on Windows
            in_root = False

        # Race each folder only once, so callers that retry with a new name
        # (e.g. tempfile.mkdtemp) still work.
        if (
            in_root
            and abs_path not in created
            and not os.path.exists(abs_path)
        ):
            real_mkdir(abs_path)
            created.append(abs_path)

        return real_mkdir(path, *args, **kwargs)

    # os.makedirs calls os.mkdir for each missing folder, so this covers both
    monkeypatch.setattr(os, 'mkdir', mkdir)
    return created

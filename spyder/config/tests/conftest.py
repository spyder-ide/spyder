# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Tests for the `spyder.config`."""

# Third party imports
import pytest

# Local imports
from spyder.config.user import DefaultsConfig, UserConfig
from spyder.py3compat import PY2


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
    if PY2:
        # strings are quoted in Python2 but not in Python3
        ini_contents += "[section]\noption = 'value'\n\n"
    else:
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

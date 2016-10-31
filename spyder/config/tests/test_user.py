# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Tests for config/user.py
"""

# Third party imports
import pytest

# Local imports
from spyder.config.user import UserConfig
from spyder.py3compat import PY2

@pytest.fixture
def userconfig(tmpdir, monkeypatch):
    monkeypatch.setattr('spyder.config.user.get_conf_path', lambda: str(tmpdir))
    inifile = tmpdir.join('foo.ini')
    iniContents = '[main]\nversion = 1.0.0\n\n'
    if PY2: # strings are quoted in Python2 but not in Python3
        iniContents += "[section]\noption = 'value'\n\n"
    else:
        iniContents += "[section]\noption = value\n\n"
    inifile.write(iniContents)
    return UserConfig('foo', defaults={}, subfolder=True,
                      version='1.0.0', raw_mode=True)

def test_userconfig_get_string_from_inifile(userconfig):
    assert userconfig.get('section', 'option') == 'value'

def test_userconfig_get_does_not_eval_functions(userconfig):
    # regression test for issue #3354
    userconfig.set('section', 'option', 'print("foo")')
    assert userconfig.get('section', 'option') == 'print("foo")'

def test_userconfig_set_with_string(userconfig):
    userconfig.set('section', 'option', 'new value')
    with open(userconfig.filename()) as inifile:
        iniContents = inifile.read()
    expected = '[main]\nversion = 1.0.0\n\n'
    if PY2:
        expected += "[section]\noption = 'new value'\n\n"
    else:
        expected += "[section]\noption = new value\n\n"
    assert iniContents == expected


if __name__ == "__main__":
    pytest.main()

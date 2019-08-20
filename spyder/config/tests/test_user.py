# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for config/user.py."""

# Standard library imports
import os

# Third party imports
import pytest

# Local imports
from spyder.config.main import CONF_VERSION, DEFAULTS
from spyder.config.user import NoDefault, UserConfig
from spyder.py3compat import PY2
from spyder.py3compat import configparser as cp
from spyder.utils.fixtures import tmpconfig


# --- Default config tests
# ----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "test_input, expected",
    [
        (('sec', 'opt', 'val'), '[sec][opt] = val\n'),
        (('sec', 'opt', 50), '[sec][opt] = 50\n'),
        (('sec', 'opt', [50]), '[sec][opt] = [50]\n'),
        (('sec', 'opt', (50, 2)), '[sec][opt] = (50, 2)\n'),
        (('sec', 'opt', {50}), '[sec][opt] = {}\n'.format(
            'set([50])' if PY2 else '{50}')),
        (('sec', 'opt', {'k': 50}), "[sec][opt] = {'k': 50}\n"),
        (('sec', 'opt', False), '[sec][opt] = False\n'),
        (('sec', 'opt', True), '[sec][opt] = True\n'),
        (('sec space', 'opt', True), '[sec space][opt] = True\n'),
        (('sec space', 'opt space', True), '[sec space][opt space] = True\n'),
    ]
)
def test_default_config_set(defaultconfig, capsys, test_input, expected):
    section, option, value = test_input
    defaultconfig._set(section, option, value, verbose=True)
    assert defaultconfig.sections() == [section]

    captured = capsys.readouterr()
    assert captured.out == expected


def test_default_config_save_write(defaultconfig):
    defaultconfig._save()


def test_default_config_set_defaults(defaultconfig):
    defaults = [('main2', {'opt': 1})]
    defaultconfig.set_defaults(defaults)
    assert 'main2' in defaultconfig.sections()


# --- User config tests
# ============================================================================
# --- Helpers and checkers
@pytest.mark.parametrize('value,expected', [
    ('3.2.1', '3.2'),
    ('3.2.0', '3.2'),
])
def test_userconfig_get_minor_version(value, expected):
    result = UserConfig._get_minor_version(value)
    assert result == expected


@pytest.mark.parametrize('value,expected', [
    ('3.2.1', '3'),
    ('0.2.0', '0'),
])
def test_userconfig_get_major_version(value, expected):
    result = UserConfig._get_major_version(value)
    assert result == expected


@pytest.mark.parametrize('test_version', [
    ('abc'),
    ('x.x.x'),
    ('1.0'),
    ('-1.0'),
    ('-1.0.0'),
    (''),
])
def test_userconfig_check_version(tmpdir, test_version, userconfig):
    name = 'spyder-test'
    path = str(tmpdir)
    with pytest.raises(ValueError):
        UserConfig(name=name, path=path, defaults=DEFAULTS,
                   load=False, version=test_version, raw_mode=True)

    # Check that setting a wrong version also runs the version checks
    with pytest.raises(ValueError):
        userconfig.set_version(test_version)


def test_userconfig_check_defaults(tmpdir, capsys):
    name = 'foobar'
    path = str(tmpdir)
    conf = UserConfig(name=name, path=path, defaults={},
                      load=False, version='1.0.0', backup=False,
                      raw_mode=True)

    conf._check_defaults({})
    conf._check_defaults({'option2': 'value2'})
    conf._check_defaults([])
    conf._check_defaults([('sec', {'opt1': 'val1'})])

    with pytest.raises(AssertionError):
        conf._check_defaults([(123, {'opt1': 'val1'})])

    with pytest.raises(AssertionError):
        conf._check_defaults([('sec', {123: 'val1'})])

    with pytest.raises(ValueError):
        conf._check_defaults({1, 2, 3})

    with pytest.raises(ValueError):
        conf._check_defaults('asd')


def test_userconfig_check_section_option(userconfig):
    section = userconfig._check_section_option(None, 'version')
    assert section == userconfig.DEFAULT_SECTION_NAME

    section = userconfig._check_section_option(None, 'opt')
    assert section == userconfig.DEFAULT_SECTION_NAME

    section = userconfig._check_section_option('sec', 'opt')
    assert section == 'sec'

    # Check with invalid section
    with pytest.raises(RuntimeError):
        section = userconfig._check_section_option(123, 'opt')

    # Check with invalid option
    with pytest.raises(RuntimeError):
        section = userconfig._check_section_option(None, 123)


def test_userconfig_load_from_ini(tmpdir, capsys):
    # Test error on loading
    name = 'foobar'
    path = str(tmpdir)
    fpath = os.path.join(path, '{}.ini'.format(name))
    with open(fpath, 'w') as fh:
        fh.write('[sec\n')

    conf = UserConfig(name=name, path=path, defaults=DEFAULTS,
                      load=True, version=CONF_VERSION, backup=False,
                      raw_mode=True)
    assert conf.get_config_fpath() == fpath

    captured = capsys.readouterr()
    assert 'Warning' in captured.out


# --- Public API
def test_userconfig_get_version(userconfig, tmpconfig):
    assert tmpconfig.get_version() == CONF_VERSION
    assert userconfig.get_version() == '1.0.0'
    userconfig.remove_option('main', 'version')
    assert userconfig.get_version() == '0.0.0'


def test_userconfig_set_version(userconfig):
    version = '1000.1000.1000'
    userconfig.set_version(version)
    assert userconfig.get_version() == version


def test_userconfig_reset_to_defaults(tmpdir):
    name = 'foobar'
    path = str(tmpdir)
    defaults = [('main', {'opt': False}), ('test', {'opt': False})]
    conf = UserConfig(name=name, path=path, defaults=defaults,
                      load=False, version='1.0.0', backup=False,
                      raw_mode=True)
    # Skip section, should go to default
    assert conf.defaults == defaults
    conf.set(None, 'opt', True)
    assert conf.get(None, 'opt') is True
    conf.reset_to_defaults()
    assert conf.get(None, 'opt') is False

    # Provide section, should go to sectio
    assert conf.defaults == defaults
    conf.set('test', 'opt', True)
    assert conf.get('test', 'opt') is True
    conf.reset_to_defaults()
    assert conf.get('test', 'opt') is False


def test_userconfig_set_as_defaults(tmpdir):
    name = 'foobar'
    path = str(tmpdir)
    conf = UserConfig(name=name, path=path, defaults={},
                      load=False, version='1.0.0', backup=False,
                      raw_mode=True)

    # TODO: Is this expected? this seems inconsistent
    assert conf.defaults == [('main', {})]
    conf.set_as_defaults()
    assert conf.defaults == []


def test_userconfig_get_default(userconfig, tmpconfig):
    # Not existing and no defaults
    value = userconfig.get_default('other_section', 'other_option')
    assert value == NoDefault

    # Existing and no defaults
    value = userconfig.get_default('section', 'option')
    assert value == NoDefault

    # Existing and defaults
    value = tmpconfig.get_default('main', 'window/is_maximized')
    assert value is True


class TestUserConfigGet:

    @pytest.mark.parametrize(
        'defaults,value',
        [
            # Valid values
            ([('test', {'opt': 'value'})], 'value'),
            ([('test', {'opt': u'"éàÇÃãéèï"'})], u'"éàÇÃãéèï"'),
            ([('test', {'opt': 'éàÇÃãéèï'})], u'éàÇÃãéèï'),
            ([('test', {'opt': True})], True),
            ([('test', {'opt': UserConfig})], repr(UserConfig)),
            ([('test', {'opt': 123})], 123),
            ([('test', {'opt': 123.123})], 123.123),
            ([('test', {'opt': [1]})], [1]),
            ([('test', {'opt': {'key': 'val'}})], {'key': 'val'}),
        ]
    )
    def test_userconfig_get(self, defaults, value, tmpdir):
        name = 'foobar'
        path = str(tmpdir)
        conf = UserConfig(name=name, path=path, defaults=defaults,
                          load=False, version='1.0.0', backup=False,
                          raw_mode=True)

        assert conf.get('test', 'opt') == value

    @pytest.mark.parametrize(
        'defaults,default,raises',
        [
            # Valid values
            ([('test2', {'opt': 'value'})], 'val', True),
            ([('test2', {'opt': 'value'})], 'val', False),
            ([('test', {'opt': 'value'})], 'val', False),
        ]
    )
    def test_userconfig_get2(self, defaults, default, raises, tmpdir):
        name = 'foobar'
        path = str(tmpdir)
        conf = UserConfig(name=name, path=path, defaults=defaults,
                          load=False, version='1.0.0', backup=False,
                          raw_mode=True)

        if raises:
            with pytest.raises(cp.NoSectionError):
                conf.get('test', 'opt')
        else:
            conf.get('test', 'opt', default)

    def test_userconfig_get_string_from_inifile(self, userconfig):
        assert userconfig.get('section', 'option') == 'value'

    def test_userconfig_get_does_not_eval_functions(self, userconfig):
        # Regression test for spyder-ide/spyder#3354.
        userconfig.set('section', 'option', 'print("foo")')
        assert userconfig.get('section', 'option') == 'print("foo")'


def test_userconfig_set_default(userconfig):
    value = userconfig.get_default('section', 'option')
    assert value == NoDefault

    # TODO: Is this expected behavior? should. If no defaults are provided
    # then they cannot be set individually until set_as_defaults() is ran?
    default_value = 'foobar'
    value = userconfig.set_default('section', 'option', default_value)
    value = userconfig.get_default('section', 'option')
    assert value == NoDefault

    userconfig.set_as_defaults()
    value = userconfig.get_default('section', 'option')
    expected = "'value'" if PY2 else 'value'
    assert value == expected
    value = userconfig.set_default('section', 'option', default_value)
    value = userconfig.get_default('section', 'option')
    assert value == default_value


class TestUserConfigSet:

    @pytest.mark.parametrize(
        'defaults,value',
        [
            # Valid values
            ([('test', {'opt': 'value'})], 'other'),
            ([('test', {'opt': 'éàÇÃãéèï'})], u'ãéèï'),
            ([('test', {'opt': True})], False),
            ([('test', {'opt': UserConfig})], dict),
            ([('test', {'opt': 123})], 345),
            ([('test', {'opt': 123.123})], 345.345),
            ([('test', {'opt': [1]})], [1]),
            ([('test', {'opt': {'key': 'val'}})], {'key2': 'val2'}),
            # Value not in defaults
            ([('test', {'opt1': 'value'})], 'other'),
        ]
    )
    def test_userconfig_set_valid(self, defaults, value, tmpdir):
        name = 'foobar'
        path = str(tmpdir)
        conf = UserConfig(name=name, path=path, defaults=defaults,
                          load=False, version='1.0.0', backup=False,
                          raw_mode=True)
        conf.set('test', 'opt', value)

    @pytest.mark.parametrize(
        'defaults,value',
        [
            ([('test', {'opt': 123})], 'no'),
            ([('test', {'opt': 123.123})], 'n9'),
            ([('test', {'opt': 123.123})], 'n9'),
        ]
    )
    def test_userconfig_set_invalid(self, defaults, value, tmpdir):
        name = 'foobar'
        path = str(tmpdir)
        conf = UserConfig(name=name, path=path, defaults=defaults,
                         load=False, version='1.0.0', backup=False,
                          raw_mode=True)

        with pytest.raises(ValueError):
            conf.set('test', 'opt', value)

    def test_userconfig_set_with_string(self, userconfig):
        userconfig.set('section', 'option', 'new value')
        with open(userconfig.get_config_fpath()) as inifile:
            ini_contents = inifile.read()

        expected = '[main]\nversion = 1.0.0\n\n'
        if PY2:
            expected += "[section]\noption = 'new value'\n\n"
        else:
            expected += "[section]\noption = new value\n\n"

        assert ini_contents == expected

    def test_userconfig_set_percentage_string(self, userconfig):
        """Test to set an option with a '%'."""
        userconfig.set('section', 'option', '%value')
        assert userconfig.get('section', 'option') == '%value'


def test_userconfig_remove_section(userconfig):
    assert 'section' in userconfig.sections()
    userconfig.remove_section('section')
    assert 'section' not in userconfig.sections()


def test_userconfig_remove_option(userconfig):
    assert userconfig.get('section', 'option') == 'value'
    userconfig.remove_option('section', 'option')
    with pytest.raises(cp.NoOptionError):
        userconfig.get('section', 'option')


def test_userconfig_cleanup(userconfig):
    configpath = userconfig.get_config_fpath()
    assert os.path.isfile(configpath)
    userconfig.cleanup()
    assert not os.path.isfile(configpath)


# --- SpyderUserConfig tests
# ============================================================================
# --- Compatibility API
class TestSpyderConfigApplyPatches:

    def test_spyderconfig_apply_configuration_patches_42(
            self, spyderconfig_patches_42):
        # Check that the value is updated
        value = spyderconfig_patches_42.get('ipython_console',
                                            'startup/run_lines')
        expected_value = 'value1; value2'
        assert value == expected_value

    def test_spyderconfig_apply_configuration_patches_45(
            self, spyderconfig_patches_45):
        # Check that the value is not updated
        value = spyderconfig_patches_45.get('ipython_console',
                                            'startup/run_lines')
        expected_value = 'value1,value2'
        assert value == expected_value


def test_spyderconfig_get_defaults_path_name_from_version(spyderconfig):
    func = spyderconfig.get_defaults_path_name_from_version
    _, name = func('50.0.0')
    assert name == 'defaults-50.0.0'

    path, name = func('51.0.0')
    assert name == 'defaults-spyder-test-51.0.0'
    assert path.endswith('defaults')

    path, name = func('53.0.0')
    assert name == 'defaults-spyder-test-53.0.0'
    assert path.endswith('defaults')


if __name__ == "__main__":
    pytest.main()

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
import errno
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
    monkeypatch.setattr(
        spyder.config.base, 'running_under_pytest', lambda: False
    )
    monkeypatch.setattr(spyder.config.base, 'get_safe_mode', lambda: False)
    monkeypatch.setattr(spyder.config.base, 'get_home_dir', lambda: home)
    monkeypatch.delenv('SPYDER_CONFDIR', raising=False)
    monkeypatch.setenv('XDG_CONFIG_HOME', osp.join(home, '.config'))


class Exited(Exception):
    """Raised instead of exiting the test process."""


@pytest.fixture(autouse=True)
def shown_messages(monkeypatch, capsys):
    """
    Never show a real message or exit the test process if a test reaches
    the error shown when the config dir is not a folder.

    Returns
    -------
    list of tuple
        For each message shown, its text and what was printed to stderr
        before it.
    """
    import qtpy.QtWidgets

    messages = []

    # Replace the whole class, so that no other kind of message can be shown
    class FakeMessageBox:
        Ok = qtpy.QtWidgets.QMessageBox.Ok

        @staticmethod
        def critical(parent, title, text, buttons):
            messages.append((text, capsys.readouterr().err))

    def fake_exit(code):
        raise Exited(code)

    monkeypatch.setattr(qtpy.QtWidgets, 'QMessageBox', FakeMessageBox)
    monkeypatch.setattr(spyder.config.base.os, '_exit', fake_exit)
    return messages


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


def test_get_conf_path_concurrent_creation(
    tmp_path, monkeypatch, racing_mkdir
):
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
    monkeypatch.setattr(
        spyder.config.base, 'running_under_pytest', lambda: True
    )
    monkeypatch.setattr(
        spyder.config.base, 'get_clean_conf_dir', lambda: clean_dir
    )
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


@pytest.fixture
def not_a_folder_error(qapp, monkeypatch, shown_messages):
    """
    Show the (mocked) error message for a config dir that is not a folder,
    as outside our tests.
    """
    monkeypatch.setattr(
        spyder.config.base, 'running_under_pytest', lambda: False
    )
    monkeypatch.setattr(spyder.config.base, '_can_show_message', lambda: True)
    return shown_messages


def check_not_a_folder_error(messages, excinfo, path):
    """Check the error message was shown for `path` and Spyder exited."""
    assert excinfo.value.args == (1,)
    assert len(messages) == 1
    text, stderr = messages[0]
    escaped_path = str(path).replace('&', '&amp;')
    assert f"<b>{escaped_path}</b> exists in your system but" in text
    assert f"Error: {path} exists but is not a folder" in stderr


@pytest.mark.parametrize('app_exists', [True, False])
def test_get_conf_path_default_dir_is_file(
    tmp_path, monkeypatch, not_a_folder_error, app_exists
):
    """
    Test that get_conf_path shows an error message and exits for the default
    location if there's a file in its place.
    """
    import qtpy.QtWidgets

    # Check that a QApplication is created if there's none, without creating
    # a second one in the test process
    created_apps = []
    if not app_exists:
        class FakeApp:
            @staticmethod
            def instance():
                return None

            def __init__(self, argv):
                created_apps.append(argv)

            def setApplicationName(self, name):
                created_apps.append(name)

        monkeypatch.setattr(qtpy.QtWidgets, 'QApplication', FakeApp)

    # Use a name with HTML special characters to check it's escaped
    tmp_path = tmp_path / 'a&b'
    tmp_path.mkdir()
    use_default_conf_dir(monkeypatch, str(tmp_path))
    subfolder = spyder.config.base.get_conf_subfolder()
    if sys.platform.startswith('linux'):
        os.makedirs(tmp_path / '.config')
        conf_dir = tmp_path / '.config' / subfolder
    else:
        conf_dir = tmp_path / subfolder
    conf_dir.touch()

    with pytest.raises(Exited) as excinfo:
        spyder.config.base.get_conf_path()

    check_not_a_folder_error(not_a_folder_error, excinfo, conf_dir)
    assert conf_dir.is_file()
    if app_exists:
        assert created_apps == []
    else:
        assert created_apps == [['Spyder', '--no-sandbox'], 'Spyder']


def fake_stat_error(monkeypatch, path, make_error):
    """Make os.stat fail for `path` with the error given by `make_error`."""
    real_stat = os.stat

    def fake_stat(stat_path, *args, **kwargs):
        if str(stat_path) == str(path):
            raise make_error()
        return real_stat(stat_path, *args, **kwargs)

    monkeypatch.setattr(spyder.config.base.os, 'stat', fake_stat)


@pytest.mark.parametrize(
    'kind',
    [
        'file',
        'parent_file',
        'parent_file_windows',
        'broken_symlink',
        'broken_symlink_through_file',
        'broken_symlink_parent',
        'symlink_loop_parent',
        'symlink_loop_parent_windows',
    ]
)
def test_get_conf_path_custom_dir_not_a_folder(
    tmp_path, monkeypatch, not_a_folder_error, kind
):
    """
    Test that get_conf_path shows an error message and exits if a custom
    config dir, or one of its parents, exists but is not a folder.
    """
    if kind == 'file':
        conf_dir = tmp_path / 'conf'
        conf_dir.touch()
        blocking_path = conf_dir
    elif kind.startswith('parent_file'):
        blocking_path = tmp_path / 'parent'
        blocking_path.touch()
        conf_dir = blocking_path / 'conf'

        if kind == 'parent_file_windows':
            # Windows gives this error when creating a folder inside a file
            def makedirs(*args, **kwargs):
                raise FileNotFoundError

            monkeypatch.setattr(spyder.config.base.os, 'makedirs', makedirs)
    else:
        if kind == 'broken_symlink':
            blocking_path = conf_dir = tmp_path / 'conf'
            target = tmp_path / 'missing'
        elif kind == 'broken_symlink_through_file':
            blocking_path = conf_dir = tmp_path / 'conf'
            (tmp_path / 'file').touch()
            target = tmp_path / 'file' / 'missing'
        elif kind == 'broken_symlink_parent':
            blocking_path = tmp_path / 'parent'
            conf_dir = blocking_path / 'conf'
            target = tmp_path / 'missing'
        else:
            blocking_path = tmp_path / 'loop'
            conf_dir = blocking_path / 'conf'
            target = blocking_path

        try:
            blocking_path.symlink_to(target)
        except OSError:
            pytest.skip("Can't create symlinks")

        if kind == 'symlink_loop_parent_windows':
            # Windows gives this error for a symlink loop
            def stat_error():
                error = OSError(errno.EINVAL, "Invalid argument")
                error.winerror = 1921  # ERROR_CANT_RESOLVE_FILENAME
                return error

            fake_stat_error(monkeypatch, blocking_path, stat_error)

    monkeypatch.setenv('SPYDER_CONFDIR', str(conf_dir))

    with pytest.raises(Exited) as excinfo:
        spyder.config.base.get_conf_path()

    check_not_a_folder_error(not_a_folder_error, excinfo, blocking_path)


def test_get_conf_path_xdg_config_home_not_a_folder(
    tmp_path, monkeypatch, not_a_folder_error
):
    """
    Test that get_conf_path shows an error message and exits on Linux if
    $XDG_CONFIG_HOME exists but is not a folder.
    """
    use_default_conf_dir(monkeypatch, str(tmp_path))
    monkeypatch.setattr(spyder.config.base.sys, 'platform', 'linux')
    xdg_config_home = tmp_path / '.config'
    xdg_config_home.touch()

    with pytest.raises(Exited) as excinfo:
        spyder.config.base.get_conf_path()

    check_not_a_folder_error(not_a_folder_error, excinfo, xdg_config_home)


@pytest.mark.parametrize('missing', ['parent', 'root'])
def test_get_conf_path_missing_parent_not_shown(
    tmp_path, monkeypatch, not_a_folder_error, missing
):
    """
    Test that get_conf_path raises the error, instead of showing a message,
    if a parent of the config dir, or even its root (e.g. a missing drive
    on Windows), doesn't exist.
    """
    monkeypatch.setenv('SPYDER_CONFDIR', str(tmp_path / 'missing' / 'conf'))

    # Error given by a missing parent
    def makedirs(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(spyder.config.base.os, 'makedirs', makedirs)

    if missing == 'root':
        # Nothing exists, not even the root, which can't be accessed (e.g.
        # an unreachable network drive)
        def stat(*args, **kwargs):
            error = OSError(errno.EINVAL, "Invalid argument")
            error.winerror = 1921
            raise error

        monkeypatch.setattr(
            spyder.config.base.osp, 'lexists', lambda path: False
        )
        monkeypatch.setattr(
            spyder.config.base.osp, 'isdir', lambda path: False
        )
        monkeypatch.setattr(spyder.config.base.os, 'stat', stat)

    with pytest.raises(FileNotFoundError):
        spyder.config.base.get_conf_path()

    assert not_a_folder_error == []


@pytest.mark.skipif(
    os.name == 'nt' or os.geteuid() == 0,
    reason="Needs POSIX permissions and a non-root user"
)
def test_get_conf_path_inaccessible_folder_not_shown(
    tmp_path, monkeypatch, not_a_folder_error
):
    """
    Test that get_conf_path raises the error, instead of showing a message,
    if the config dir is a symlink to a folder that can't be accessed.
    """
    locked = tmp_path / 'locked'
    (locked / 'conf').mkdir(parents=True)
    link = tmp_path / 'link'
    link.symlink_to(locked / 'conf')
    monkeypatch.setenv('SPYDER_CONFDIR', str(link / 'conf'))

    locked.chmod(0)
    try:
        with pytest.raises(OSError):
            spyder.config.base.get_conf_path()
    finally:
        locked.chmod(0o700)

    assert not_a_folder_error == []


@pytest.mark.parametrize(
    'error_number, winerror',
    [
        (errno.EACCES, None),
        (errno.EPERM, None),
        (errno.EIO, None),
        (getattr(errno, 'ESTALE', errno.EIO), None),
        # The folder was removed after checking that it exists
        (errno.ENOENT, None),
        # ERROR_NETNAME_DELETED, which has EINVAL as errno on Windows
        (errno.EINVAL, 64),
    ]
)
def test_get_conf_path_folder_error_not_shown(
    tmp_path, monkeypatch, not_a_folder_error, error_number, winerror
):
    """
    Test that get_conf_path raises the error, instead of showing a message,
    if the config dir (e.g. a symlink to a network folder) exists but can't
    be accessed.
    """
    conf_dir = tmp_path / 'conf'
    conf_dir.mkdir()
    monkeypatch.setenv('SPYDER_CONFDIR', str(conf_dir))

    def stat_error():
        error = OSError(error_number, os.strerror(error_number))
        if winerror is not None:
            error.winerror = winerror
        return error

    # Folder that can't be accessed
    fake_stat_error(monkeypatch, conf_dir, stat_error)
    monkeypatch.setattr(spyder.config.base.osp, 'isdir', lambda path: False)

    def makedirs(*args, **kwargs):
        raise FileExistsError

    monkeypatch.setattr(spyder.config.base.os, 'makedirs', makedirs)

    with pytest.raises(FileExistsError):
        spyder.config.base.get_conf_path()

    assert not_a_folder_error == []


def test_get_conf_path_not_a_folder_in_tests(
    tmp_path, monkeypatch, shown_messages
):
    """
    Test that get_conf_path raises the error, instead of showing a message
    and exiting, in our tests if the config dir exists but is not a folder.
    """
    conf_dir = tmp_path / 'conf'
    conf_dir.touch()
    monkeypatch.setattr(
        spyder.config.base, 'get_clean_conf_dir', lambda: str(conf_dir)
    )

    with pytest.raises(FileExistsError):
        spyder.config.base.get_conf_path()

    assert shown_messages == []


@pytest.mark.parametrize(
    'platform, env, expected',
    [
        ('darwin', {}, True),
        ('win32', {}, True),
        ('darwin', {'QT_QPA_PLATFORM': 'offscreen'}, False),
        ('darwin', {'QT_QPA_PLATFORM': 'OFFSCREEN'}, False),
        ('win32', {'QT_QPA_PLATFORM': 'minimal'}, False),
        ('linux', {}, False),
        ('linux', {'DISPLAY': ':0'}, True),
        ('linux', {'WAYLAND_DISPLAY': 'wayland-0'}, True),
        ('linux', {'QT_QPA_PLATFORM': 'xcb'}, False),
        ('linux', {'QT_QPA_PLATFORM': 'xcb', 'DISPLAY': ':0'}, True),
        ('linux', {'QT_QPA_PLATFORM': 'wayland', 'DISPLAY': ':0'}, False),
        (
            'linux',
            {'QT_QPA_PLATFORM': 'wayland', 'WAYLAND_DISPLAY': 'wayland-0'},
            True,
        ),
        ('linux', {'QT_QPA_PLATFORM': 'offscreen', 'DISPLAY': ':0'}, False),
        ('linux', {'QT_QPA_PLATFORM': 'eglfs'}, True),
    ]
)
def test_can_show_message(monkeypatch, platform, env, expected):
    """Test when the error message for the config dir can be shown."""
    monkeypatch.setattr(spyder.config.base.sys, 'platform', platform)
    for env_var in ['DISPLAY', 'WAYLAND_DISPLAY', 'QT_QPA_PLATFORM']:
        monkeypatch.delenv(env_var, raising=False)
    for env_var, value in env.items():
        monkeypatch.setenv(env_var, value)

    assert spyder.config.base._can_show_message() == expected


@pytest.mark.parametrize('case', ['cant_show', 'qt_error'])
def test_not_a_folder_error_exits(
    qapp, monkeypatch, capsys, shown_messages, case
):
    """
    Test that Spyder prints the error and exits if the error message can't
    be shown.
    """
    import qtpy.QtWidgets

    if case == 'cant_show':
        monkeypatch.setattr(
            spyder.config.base, '_can_show_message', lambda: False
        )
    else:
        monkeypatch.setattr(
            spyder.config.base, '_can_show_message', lambda: True
        )

        def critical(*args):
            shown_messages.append(args)
            raise RuntimeError("Qt error")

        monkeypatch.setattr(qtpy.QtWidgets.QMessageBox, 'critical', critical)

    with pytest.raises(Exited) as excinfo:
        spyder.config.base._show_not_a_folder_error('/path/to/conf')

    assert excinfo.value.args == (1,)
    assert (
        "Error: /path/to/conf exists but is not a folder"
        in capsys.readouterr().err
    )
    assert len(shown_messages) == (1 if case == 'qt_error' else 0)


def test_get_conf_paths_concurrent_creation(
    tmp_path, monkeypatch, racing_mkdir
):
    """
    Test that get_conf_paths doesn't fail if another process creates the test
    site config dirs at the same time.
    """
    monkeypatch.setattr(
        spyder.config.base.tempfile, 'gettempdir', lambda: str(tmp_path)
    )
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

# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
"""Tests for programs.py"""

# Standard library imports
import os
import os.path as osp
import sys

# Third party impors
from flaky import flaky
import pytest

# Local imports
from spyder.utils.programs import (check_version, find_program,
                                   get_application_icon,
                                   get_installed_applications, get_temp_dir,
                                   is_module_installed, is_python_interpreter,
                                   is_python_interpreter_valid_name,
                                   open_files_with_application,
                                   parse_linux_desktop_entry,
                                   run_python_script_in_terminal, shell_split)

if os.name == 'nt':
    python_dir = os.environ['PYTHON'] if os.environ.get('CI', None) else ''
    VALID_INTERPRETER = os.path.join(python_dir, 'python.exe')
    VALID_W_INTERPRETER = os.path.join(python_dir, 'pythonw.exe')
    INVALID_INTERPRETER = os.path.join(python_dir, 'Scripts', 'ipython.exe')
else:
    if sys.platform.startswith('linux'):
        home_dir = os.environ['HOME']
    else:
        # Parent Miniconda dir in macOS Azure VMs
        home_dir = os.path.join('/usr', 'local')
    VALID_INTERPRETER = os.path.join(home_dir, 'miniconda', 'bin', 'python')
    VALID_W_INTERPRETER = os.path.join(home_dir, 'miniconda', 'bin', 'pythonw')
    INVALID_INTERPRETER = os.path.join(home_dir, 'miniconda', 'bin', 'ipython')


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def scriptpath(tmpdir):
    """Save a basic Python script in a file."""
    script = ("with open('out.txt', 'w') as f:\n"
              "    f.write('done')\n")
    scriptpath = tmpdir.join('write-done.py')
    scriptpath.write(script)
    return scriptpath


@pytest.fixture
def scriptpath_with_blanks(tmpdir):
    """Save a basic Python script in a file."""
    name_dir = 'test dir'
    if not osp.exists(name_dir):
        os.mkdir(name_dir)
    os.chdir(name_dir)
    tmpdir.join(name_dir)
    script = ("with open('out.txt', 'w') as f:\n"
              "    f.write('done')\n")
    scriptpath = tmpdir.join('write-done.py')
    scriptpath.write(script)
    return scriptpath

# =============================================================================
# ---- Tests
# =============================================================================
@pytest.mark.skipif((sys.platform.startswith('linux') or
                     os.environ.get('CI', None) is None),
                    reason='It only runs in CI services and '
                           'Linux does not have pythonw executables.')
def test_is_valid_w_interpreter():
    assert is_python_interpreter(VALID_W_INTERPRETER)


@flaky(max_runs=3)
@pytest.mark.skipif(
    os.environ.get('CI', None) is None,
    reason='fails sometimes locally')
def test_run_python_script_in_terminal(scriptpath, qtbot):
    """
    Test running a Python script in an external terminal when specifying
    explicitely the working directory.
    """
    # Run the script
    outfilepath = osp.join(scriptpath.dirname, 'out.txt')
    run_python_script_in_terminal(
        scriptpath.strpath, scriptpath.dirname, '', False, False, '')
    qtbot.waitUntil(lambda: osp.exists(outfilepath), timeout=5000)
    # Assert the result.
    with open(outfilepath, 'r') as txtfile:
        res = txtfile.read()
    assert res == 'done'


@flaky(max_runs=3)
@pytest.mark.skipif(
    os.environ.get('CI', None) is None,
    reason='fails sometimes locally')
def test_run_python_script_in_terminal_blank_wdir(scriptpath_with_blanks,
                                                  qtbot):
    """
    Test running a Python script in an external terminal when specifying
    explicitely the working directory.
    """
    # Run the script
    outfilepath = osp.join(scriptpath_with_blanks.dirname, 'out.txt')
    run_python_script_in_terminal(
        scriptpath_with_blanks.strpath, scriptpath_with_blanks.dirname,
        '', False, False, '')
    qtbot.waitUntil(lambda: osp.exists(outfilepath), timeout=5000)
    # Assert the result.
    with open(outfilepath, 'r') as txtfile:
        res = txtfile.read()
    assert res == 'done'


@flaky(max_runs=3)
@pytest.mark.skipif(
    os.environ.get('CI', None) is None,
    reason='fails sometimes locally')
def test_run_python_script_in_terminal_with_wdir_empty(scriptpath, qtbot):
    """
    Test running a Python script in an external terminal without specifying
    the working directory.
    """
    # Run the script.
    if sys.platform == 'darwin':
        outfilepath = osp.join(osp.expanduser('~'), 'out.txt')
    else:
        outfilepath = osp.join(os.getcwd(), 'out.txt')

    run_python_script_in_terminal(scriptpath.strpath, '', '', False, False, '')
    qtbot.waitUntil(lambda: osp.exists(outfilepath), timeout=5000)
    # Assert the result.
    with open(outfilepath, 'r') as txtfile:
        res = txtfile.read()
    assert res == 'done'


@pytest.mark.skipif(os.environ.get('CI', None) is None,
                    reason='It only runs in CI services.')
def test_is_valid_interpreter():
    assert is_python_interpreter(VALID_INTERPRETER)


@pytest.mark.skipif(os.environ.get('CI', None) is None,
                    reason='It only runs in CI services.')
def test_is_invalid_interpreter():
    assert not is_python_interpreter(INVALID_INTERPRETER)


def test_is_valid_interpreter_name():
    names = ['python', 'pythonw', 'python2.7', 'python3.5', 'python.exe', 'pythonw.exe']
    assert all([is_python_interpreter_valid_name(n) for n in names])

def test_find_program():
    """Test if can find the program."""
    assert find_program('git')

def test_shell_split():
    """Test if the text can be split using shell-like sintax."""
    assert shell_split('-q -o -a') == ['-q', '-o', '-a']
    assert shell_split('-q "d:\\Python de xxxx\\t.txt" -o -a') == \
           ['-q', 'd:\\Python de xxxx\\t.txt', '-o', '-a']

def test_check_version():
    """Test the compare function for versions."""
    assert check_version('0.9.4-1', '0.9.4', '>=')
    assert check_version('3.0.0rc1', '3.0.0', '<')
    assert check_version('1.0', '1.0b2', '>')

def test_is_module_installed():
    """Test if a module with the proper version is installed"""
    assert is_module_installed('qtconsole', '>=4.5')
    assert not is_module_installed('IPython', '>=1.0;<3.0')
    assert is_module_installed('jedi', '>=0.7.0')


@pytest.mark.skipif(os.name == 'nt' and os.environ.get('AZURE') is not None,
                    reason="Fails on Windows/Azure")
def test_is_module_installed_with_custom_interpreter():
    """Test if a module with the proper version is installed"""
    current = sys.executable
    assert is_module_installed('qtconsole', '>=4.5', interpreter=current)
    assert not is_module_installed('IPython', '>=1.0;<3.0', interpreter=current)
    assert is_module_installed('jedi', '>=0.7.0', interpreter=current)


def test_get_temp_dir_ensure_dir_exists():
    """Test that the call to get_temp_dir creates the dir when it doesn't exists
    """
    temp_dir = get_temp_dir(suffix='test')
    assert os.path.exists(temp_dir)

    os.rmdir(temp_dir)

    another_call = get_temp_dir(suffix='test')

    assert os.path.exists(another_call)
    assert another_call == temp_dir


def test_get_installed_apps_and_icons(qtbot):
    apps = get_installed_applications()
    assert apps
    for app in apps:
        fpath = apps[app]
        icon = get_application_icon(fpath)
        assert icon
        assert osp.isdir(fpath) or osp.isfile(fpath)


@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="Test for linux only")
def test_parse_linux_desktop_entry():
    apps = get_installed_applications()
    for app in apps:
        fpath = apps[app]
        data = parse_linux_desktop_entry(fpath)
        assert data

        for key in ['name', 'icon_path', 'hidden', 'exec', 'type', 'fpath']:
            assert key in data

        assert fpath == data['fpath']


def test_open_files_with_application(tmp_path):
    fpath = tmp_path / 'file space.txt'
    fpath.write_text(u'Hello')
    fpath_2 = tmp_path / 'file2.txt'
    fpath_2.write_text(u'Hello 2')

    if os.name == 'nt':
        ext = '.exe'
        path_obj = tmp_path / ("some-new app" + ext)
        path_obj.write_bytes(b'\x00\x00')
        app_path = str(path_obj)
    elif sys.platform == 'darwin':
        ext = '.app'
        path_obj = tmp_path / ("some-new app" + ext)
        path_obj.mkdir()
        app_path = str(path_obj)
    else:
        ext = '.desktop'
        path_obj = tmp_path / ("some-new app" + ext)
        path_obj.write_text(u'''
[Desktop Entry]
Name=Suer app
Type=Application
Exec=/something/bleerp
Icon=/blah/blah.xpm
''')
        app_path = str(path_obj)

    fnames = [str(fpath), str(fpath_2)]
    return_codes = open_files_with_application(app_path, fnames)
    assert 0 not in return_codes.values()

    # Test raises
    with pytest.raises(ValueError):
        return_codes = open_files_with_application('not-valid.ext', fnames)


if __name__ == '__main__':
    pytest.main()

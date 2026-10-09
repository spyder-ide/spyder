# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------

"""Tests for the plugin."""

# Standard library imports
import os
import sys

# Third party imports
import pytest
from spyder_kernels.utils.pythonenv import is_conda_env

# Local imports
from spyder.config.base import running_in_ci
from spyder.plugins.maininterpreter.plugin import MainInterpreter
from spyder.utils.conda import find_local_venv_interpreter, has_spyder_kernels


@pytest.fixture
def maininterpreter(qtbot):
    """Set up PathManager."""
    plugin = MainInterpreter(None)
    qtbot.addWidget(plugin.get_container())
    return plugin


@pytest.mark.skipif(
    not is_conda_env(sys.prefix), reason="Requires conda to be installed"
)
@pytest.mark.skipif(not running_in_ci(), reason="Only meant for CIs")
def test_conda_interpreters(maininterpreter, qtbot):
    """Test info from conda interpreters."""
    container = maininterpreter.get_container()
    container._interpreter = ""

    name_base = "Conda: base"
    name_test = "Conda: jedi-test-env"

    # Wait until envs are computed
    qtbot.wait(4000)

    # Update to the base conda environment
    path_base, version = container.envs[name_base]
    expected = "Conda: base ({})".format(version)
    assert expected == container._get_env_info(path_base)

    # Update to the foo conda environment
    path_foo, version = container.envs[name_test]
    expected = "Conda: jedi-test-env ({})".format(version)
    assert expected == container._get_env_info(path_foo)


def test_pyenv_interpreters(maininterpreter, qtbot):
    """Test info from pyenv interpreters."""
    container = maininterpreter.get_container()

    version = "Python 3.6.6"
    name = "pyenv: test"
    interpreter = os.sep.join(["some-other", "bin", "python"])
    container.envs = {name: (interpreter, version)}
    container.path_to_env = {interpreter: name}
    assert "pyenv: test (Python 3.6.6)" == container._get_env_info(interpreter)


@pytest.mark.skipif(sys.platform != "darwin", reason="Only valid on Mac")
def test_internal_interpreter(maininterpreter, qtbot, mocker):
    """Test info from internal interpreter."""
    container = maininterpreter.get_container()

    interpreter = os.sep.join(["Spyder.app", "Contents", "MacOS", "Python"])
    name = "system:"
    version = "Python 3.6.6"
    container.envs = {name: (interpreter, version)}
    container.path_to_env = {interpreter: name}
    assert "system: (Python 3.6.6)" == container._get_env_info(interpreter)


def test_find_local_venv_interpreter_found(tmp_path):
    """Test detection when a valid .venv exists in the project."""
    venv_dir = tmp_path / ".venv"
    bin_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
    bin_dir.mkdir(parents=True)
    python_name = "python.exe" if os.name == "nt" else "python"
    python_path = bin_dir / python_name
    python_path.touch()

    result = find_local_venv_interpreter(str(tmp_path))
    assert result == str(python_path)


def test_find_local_venv_interpreter_no_venv(tmp_path):
    """Test that None is returned when there's no .venv folder."""
    result = find_local_venv_interpreter(str(tmp_path))
    assert result is None


def test_find_local_venv_interpreter_broken_venv(tmp_path):
    """Test that None is returned when .venv exists but has no binary."""
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()

    result = find_local_venv_interpreter(str(tmp_path))
    assert result is None


def test_has_spyder_kernels_true(mocker):
    """Test detection when spyder-kernels is importable."""
    mock_result = mocker.Mock()
    mock_result.returncode = 0
    mocker.patch("subprocess.run", return_value=mock_result)

    assert has_spyder_kernels("/fake/path/python") is True


def test_has_spyder_kernels_false(mocker):
    """Test detection when spyder-kernels is not importable."""
    mock_result = mocker.Mock()
    mock_result.returncode = 1
    mocker.patch("subprocess.run", return_value=mock_result)

    assert has_spyder_kernels("/fake/path/python") is False


def test_auto_detect_venv_switches_interpreter(
    maininterpreter, qtbot, mocker, tmp_path
):
    """Test that a found .venv with spyder-kernels gets auto-selected."""
    venv_dir = tmp_path / ".venv"
    bin_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
    bin_dir.mkdir(parents=True)
    python_name = "python.exe" if os.name == "nt" else "python"
    python_path = bin_dir / python_name
    python_path.touch()

    mocker.patch(
        "spyder.plugins.maininterpreter.plugin.has_spyder_kernels",
        return_value=True,
    )
    mocker.patch.object(maininterpreter, "get_plugin", return_value=None)
    mock_switch = mocker.patch.object(
        maininterpreter, "set_custom_interpreter"
    )

    maininterpreter._auto_detect_venv(str(tmp_path))

    mock_switch.assert_called_once_with(str(python_path), manual=False)

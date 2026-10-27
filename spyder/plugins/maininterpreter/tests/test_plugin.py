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
from spyder.utils.conda import find_local_venv_interpreter
from spyder.plugins.maininterpreter.plugin import (
    MainInterpreter,
    PROJECT_INTERPRETER_OPTION,
)


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
    container._interpreter = ''

    name_base = 'Conda: base'
    name_test = 'Conda: jedi-test-env'

    # Wait until envs are computed
    qtbot.wait(4000)

    # Update to the base conda environment
    path_base, version = container.envs[name_base]
    expected = 'Conda: base ({})'.format(version)
    assert expected == container._get_env_info(path_base)

    # Update to the foo conda environment
    path_foo, version = container.envs[name_test]
    expected = 'Conda: jedi-test-env ({})'.format(version)
    assert expected == container._get_env_info(path_foo)


def test_pyenv_interpreters(maininterpreter, qtbot):
    """Test info from pyenv interpreters."""
    container = maininterpreter.get_container()

    version = 'Python 3.6.6'
    name = 'pyenv: test'
    interpreter = os.sep.join(['some-other', 'bin', 'python'])
    container.envs = {name: (interpreter, version)}
    container.path_to_env = {interpreter: name}
    assert 'pyenv: test (Python 3.6.6)' == container._get_env_info(interpreter)


@pytest.mark.skipif(sys.platform != 'darwin', reason="Only valid on Mac")
def test_internal_interpreter(maininterpreter, qtbot, mocker):
    """Test info from internal interpreter."""
    container = maininterpreter.get_container()

    interpreter = os.sep.join(['Spyder.app', 'Contents', 'MacOS', 'Python'])
    name = 'system:'
    version = 'Python 3.6.6'
    container.envs = {name: (interpreter, version)}
    container.path_to_env = {interpreter: name}
    assert 'system: (Python 3.6.6)' == container._get_env_info(interpreter)


@pytest.mark.parametrize(
    "folder",
    [".venv", "venv", "env", os.path.join(".pixi", "envs", "default")],
)
def test_find_local_venv_interpreter_folders(tmp_path, folder):
    bin_dir = tmp_path / folder / ("Scripts" if os.name == "nt" else "bin")
    bin_dir.mkdir(parents=True)
    interpreter = bin_dir / ("python.exe" if os.name == "nt" else "python")
    interpreter.touch()

    assert find_local_venv_interpreter(str(tmp_path)) == str(interpreter)


def test_find_local_venv_interpreter_not_found(tmp_path):
    # No environment folder at all
    assert find_local_venv_interpreter(str(tmp_path)) is None

    # Folder exists but has no interpreter inside
    (tmp_path / ".venv").mkdir()
    assert find_local_venv_interpreter(str(tmp_path)) is None


# ---- Project interpreter
# -----------------------------------------------------------------------------
def _make_venv(path):
    """Create a fake .venv in path and return the path to its interpreter."""
    bin_dir = path / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    bin_dir.mkdir(parents=True)
    interpreter = bin_dir / ("python.exe" if os.name == "nt" else "python")
    interpreter.touch()
    return str(interpreter)


class FakeProject:
    """Minimal stand-in for a Spyder project."""

    def __init__(self, root_path, interpreter=""):
        self.root_path = str(root_path)
        self.options = {PROJECT_INTERPRETER_OPTION: interpreter}

    def get_option(self, option, **kwargs):
        return self.options.get(option)

    def set_option(self, option, value, **kwargs):
        self.options[option] = value


@pytest.fixture
def maininterpreter_conf(qtbot):
    """Plugin that is connected to Spyder's configuration."""
    from spyder.config.manager import CONF

    plugin = MainInterpreter(None, CONF)
    qtbot.addWidget(plugin.get_container())
    return plugin


@pytest.fixture
def projects(maininterpreter_conf, mocker):
    """Make the plugin see a fake Projects plugin with an active project."""
    plugin = mocker.Mock()
    mocker.patch.object(
        maininterpreter_conf, "get_plugin", return_value=plugin
    )
    return plugin


def test_project_interpreter_is_used_and_restored(
    maininterpreter_conf, projects, tmp_path
):
    """The project interpreter replaces the global one until the project is
    closed."""
    interpreter = _make_venv(tmp_path)
    projects.get_active_project.return_value = FakeProject(
        tmp_path, interpreter
    )
    maininterpreter_conf.set_conf("default", True)
    maininterpreter_conf.set_conf("custom", False)

    maininterpreter_conf._on_project_loaded(str(tmp_path))
    assert maininterpreter_conf.get_conf("executable") == interpreter
    assert maininterpreter_conf.get_conf("custom") is True
    assert maininterpreter_conf.get_conf("custom_interpreter") == interpreter

    maininterpreter_conf._on_project_closed(str(tmp_path))
    assert maininterpreter_conf.get_conf("default") is True
    assert maininterpreter_conf.get_conf("custom") is False
    assert maininterpreter_conf.get_conf("executable") != interpreter


def test_project_without_interpreter_uses_global_one(
    maininterpreter_conf, projects, tmp_path, mocker
):
    """Switching to a project with no interpreter falls back to the global
    interpreter."""
    interpreter = _make_venv(tmp_path / "with_env")
    mocker.patch(
        "spyder.plugins.maininterpreter.plugin.find_local_venv_interpreter",
        return_value=None,
    )
    maininterpreter_conf.set_conf("default", True)
    maininterpreter_conf.set_conf("custom", False)

    # Project A has an interpreter
    projects.get_active_project.return_value = FakeProject(
        tmp_path / "with_env", interpreter
    )
    maininterpreter_conf._on_project_loaded(str(tmp_path / "with_env"))
    assert maininterpreter_conf.get_conf("executable") == interpreter

    # Project B doesn't (switching projects closes the previous one first)
    maininterpreter_conf._on_project_closed(str(tmp_path / "with_env"))
    projects.get_active_project.return_value = FakeProject(tmp_path / "other")
    maininterpreter_conf._on_project_loaded(str(tmp_path / "other"))
    assert maininterpreter_conf.get_conf("default") is True
    assert maininterpreter_conf.get_conf("executable") != interpreter


def test_missing_project_interpreter_is_ignored(
    maininterpreter_conf, projects, tmp_path
):
    """A project interpreter that doesn't exist anymore is not applied."""
    gone = str(tmp_path / "gone" / "python")
    projects.get_active_project.return_value = FakeProject(tmp_path, gone)
    maininterpreter_conf.set_conf("default", True)

    maininterpreter_conf._on_project_loaded(str(tmp_path))
    assert maininterpreter_conf.get_conf("default") is True
    assert maininterpreter_conf.get_conf("executable") != gone


def test_detected_interpreter_is_saved_in_project(
    maininterpreter_conf, projects, tmp_path
):
    """A .venv found in a project without interpreter is saved and used."""
    interpreter = _make_venv(tmp_path)
    project = FakeProject(tmp_path)
    projects.get_active_project.return_value = project

    maininterpreter_conf._on_project_loaded(str(tmp_path))
    assert project.options[PROJECT_INTERPRETER_OPTION] == interpreter
    assert maininterpreter_conf.get_conf("executable") == interpreter

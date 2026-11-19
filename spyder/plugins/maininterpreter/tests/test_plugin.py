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
from spyder.config.manager import CONF
from spyder.plugins.maininterpreter.plugin import MainInterpreter


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


@pytest.fixture
def maininterpreter_with_conf(qtbot):
    """
    Set up the plugin using Spyder's configuration.

    The main interpreter options changed by a test are restored afterwards.
    """
    section = "main_interpreter"
    options = [
        "default",
        "custom",
        "custom_interpreter",
        "custom_interpreters_list",
        "executable",
    ]
    previous = {
        opt: CONF.get(section, opt)
        for opt in options
        if CONF.has_option(section, opt)
    }

    plugin = MainInterpreter(None, configuration=CONF)
    qtbot.addWidget(plugin.get_container())

    yield plugin

    for opt in options:
        if opt in previous:
            CONF.set(section, opt, previous[opt])
        elif CONF.has_option(section, opt):
            CONF.remove_option(section, opt)


def test_set_custom_interpreter_surrounding_whitespace(
    maininterpreter_with_conf
):
    """
    Check that whitespace around an interpreter set by other plugins is
    removed before saving it.

    This is a regression test for spyder-ide/spyder#24955
    """
    plugin = maininterpreter_with_conf
    plugin.set_custom_interpreter(sys.executable + "\n")

    assert plugin.get_conf("custom_interpreter") == sys.executable
    assert plugin.get_conf("executable") == sys.executable
    assert (
        sys.executable + "\n"
        not in plugin.get_conf("custom_interpreters_list")
    )


def test_custom_interpreter_option_surrounding_whitespace(
    maininterpreter_with_conf
):
    """
    Check that whitespace around the custom interpreter option is removed
    before using it as the main interpreter.

    This is a regression test for spyder-ide/spyder#24955
    """
    plugin = maininterpreter_with_conf
    plugin.set_conf("executable", "")
    plugin.set_conf("default", False)
    plugin.set_conf("custom", True)

    # This calls the container's on_interpreter_changed method
    plugin.set_conf("custom_interpreter", sys.executable + "\n")

    assert plugin.get_conf("executable") == sys.executable

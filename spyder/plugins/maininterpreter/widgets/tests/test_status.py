# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------

"""Tests for status bar widgets."""

# Standard library imports
import os
import sys

# Third party imports
import pytest


# Local imports
from spyder.plugins.statusbar.widgets.tests.test_status import status_bar
from spyder.plugins.maininterpreter.widgets.status import InterpreterStatus


@pytest.mark.skipif(not bool(os.environ.get('CI')),
                    reason="Only meant for CIs")
def test_status_bar_conda_interpreter_status(status_bar, qtbot):
    """Test status bar message with conda interpreter."""
    # Set env var to use worker
    os.environ['SPY_TEST_USE_WORKERS'] = 'True'

    # We patch where the method is used not where it is imported from
    plugin, window = status_bar
    w = InterpreterStatus(window)
    w._interpreter = ''
    plugin.add_status_widget(w)

    name_base = 'conda: base'
    name_test = 'conda: test'

    # Wait until envs are computed
    qtbot.wait(4000)

    # Update to the base conda environment
    path_base, version = w.envs[name_base]
    w.update_interpreter(path_base)
    expected = 'conda: base ({})'.format(version)
    assert w.get_tooltip() == path_base
    assert expected == w._get_env_info(path_base)

    # Update to the foo conda environment
    path_foo, version = w.envs[name_test]
    w.update_interpreter(path_foo)
    expected = 'conda: test ({})'.format(version)
    assert w.get_tooltip() == path_foo
    assert expected == w._get_env_info(path_foo)

    # Remove env var to use worker
    os.environ.pop('SPY_TEST_USE_WORKERS')


def test_status_bar_pyenv_interpreter_status(status_bar, qtbot):
    """Test status var message with pyenv interpreter."""
    plugin, window = status_bar
    w = InterpreterStatus(window)
    plugin.add_status_widget(w)

    version = 'Python 3.6.6'
    name = 'pyenv: test'
    interpreter = os.sep.join(['some-other', 'bin', 'python'])
    w.envs = {name: (interpreter, version)}
    w.path_to_env = {interpreter: name}
    w.update_interpreter(interpreter)
    assert w.get_tooltip() == interpreter
    assert 'pyenv: test (Python 3.6.6)' == w._get_env_info(interpreter)


@pytest.mark.skipif(sys.platform != 'darwin', reason="Only valid on Mac")
def test_status_bar_internal_interpreter_status(status_bar, qtbot, mocker):
    """Test status bar message with internal interpreter."""
    plugin, window = status_bar
    w = InterpreterStatus(window)
    plugin.add_status_widget(w)

    interpreter = os.sep.join(['Spyder.app', 'Contents', 'MacOS', 'Python'])
    name = 'system:'
    version = 'Python 3.6.6'
    w.envs = {name: (interpreter, version)}
    w.path_to_env = {interpreter: name}
    w.update_interpreter(interpreter)
    assert w.get_tooltip() == interpreter
    assert 'system: (Python 3.6.6)' == w._get_env_info(interpreter)

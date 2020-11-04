# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for solver.py
"""

# Third party imports
import pytest

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.plugins import SpyderPluginV2
from spyder.app.solver import find_internal_plugins, solve_plugin_dependencies
from spyder.utils.external.toposort import CircularDependencyError


# --- Mock valid plugins
# ----------------------------------------------------------------------------
class A(SpyderPluginV2):
    NAME = "A"
    REQUIRES = []
    OPTIONAL = []


class B(SpyderPluginV2):
    NAME = "B"
    REQUIRES = []
    OPTIONAL = []


class C(SpyderPluginV2):
    NAME = "C"
    REQUIRES = ["B", "A"]
    OPTIONAL = ["D", "E"]


class D(SpyderPluginV2):
    NAME = "D"
    REQUIRES = ["E"]
    OPTIONAL = ["F"]


class E(SpyderPluginV2):
    NAME = "E"


class F(SpyderPluginV2):
    NAME = "F"


# --- Mock invalid plugins
# ----------------------------------------------------------------------------
class None1(SpyderPluginV2):
    NAME = "None1"


class Self(SpyderPluginV2):
    NAME = "Self"
    REQUIRES = ["Self"]


class Circular1(SpyderPluginV2):
    NAME = "Circular1"
    REQUIRES = ["Circular2"]


class Circular2(SpyderPluginV2):
    NAME = "Circular2"
    REQUIRES = ["Circular1"]


# --- Tests
# ----------------------------------------------------------------------------
def test_solve_plugin_dependencies_none_values():
    found_plugins = [None1]
    assert solve_plugin_dependencies(found_plugins) == found_plugins


def test_solve_plugin_dependencies_self_reference():
    found_plugins = [Self]
    with pytest.raises(SpyderAPIError):
        solve_plugin_dependencies(found_plugins)


def test_solve_plugin_dependencies_circular():
    found_plugins = [Circular1, Circular2]
    with pytest.raises(CircularDependencyError):
        solve_plugin_dependencies(found_plugins)


def test_solve_plugin_dependencies_missing_optional():
    found_plugins = [A, B, C]
    assert solve_plugin_dependencies(found_plugins) == found_plugins


def test_solve_plugin_dependencies_missing_requires():
    found_plugins = [A, B, C, D]
    assert solve_plugin_dependencies(found_plugins) == found_plugins[:-1]


def test_solve_plugin_dependencies_1():
    found_plugins = [E, F, D]
    assert solve_plugin_dependencies(found_plugins) == found_plugins


def test_solve_plugin_dependencies_2():
    found_plugins = [E, D]
    assert solve_plugin_dependencies(found_plugins) == found_plugins


def test_solve_plugin_dependencies_3():
    found_plugins = [F, D]
    assert solve_plugin_dependencies(found_plugins) == [F]


def test_find_internal_plugins():
    internal = find_internal_plugins()
    assert len(internal) == 20

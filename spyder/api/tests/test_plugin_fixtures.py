# -----------------------------------------------------------------------------
# Copyright (c) 2026- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""Tests for plugin testing helpers."""

from types import SimpleNamespace

from spyder.api.plugins import tests as plugin_tests


def test_create_fixturedef_with_fixturemanager(monkeypatch):
    """Test creating a FixtureDef for pytest versions before 9."""
    kwargs = {}

    class DummyFixtureDef:
        def __init__(self, **fixture_kwargs):
            kwargs.update(fixture_kwargs)

    request = SimpleNamespace(
        config=object(),
        node=SimpleNamespace(nodeid="nodeid"),
        _fixturemanager=object(),
    )
    fixture_func = object()

    monkeypatch.setattr(plugin_tests, "FixtureDef", DummyFixtureDef)
    monkeypatch.setattr(
        plugin_tests,
        "_FIXTUREDEF_PARAMETERS",
        {
            "argname": None,
            "func": None,
            "scope": None,
            "fixturemanager": None,
            "baseid": None,
            "params": None,
        },
    )

    plugin_tests._create_fixturedef(request, "plugin_fixture", fixture_func)

    assert kwargs == {
        "argname": "plugin_fixture",
        "func": fixture_func,
        "scope": "session",
        "fixturemanager": request._fixturemanager,
        "baseid": "nodeid",
        "params": None,
    }


def test_create_fixturedef_with_config(monkeypatch):
    """Test creating a FixtureDef for pytest 9 and later."""
    kwargs = {}

    class DummyFixtureDef:
        def __init__(self, **fixture_kwargs):
            kwargs.update(fixture_kwargs)

    request = SimpleNamespace(
        config=object(),
        node=SimpleNamespace(nodeid="nodeid"),
        _fixturemanager=object(),
    )
    fixture_func = object()

    monkeypatch.setattr(plugin_tests, "FixtureDef", DummyFixtureDef)
    monkeypatch.setattr(
        plugin_tests,
        "_FIXTUREDEF_PARAMETERS",
        {
            "config": None,
            "baseid": None,
            "argname": None,
            "func": None,
            "scope": None,
            "params": None,
            "ids": None,
            "_ispytest": None,
        },
    )

    plugin_tests._create_fixturedef(request, "plugin_fixture", fixture_func)

    assert kwargs == {
        "config": request.config,
        "baseid": "nodeid",
        "argname": "plugin_fixture",
        "func": fixture_func,
        "scope": "session",
        "params": None,
        "ids": None,
        "_ispytest": True,
    }

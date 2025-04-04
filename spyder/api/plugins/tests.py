# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from __future__ import annotations
import gc
import sys
import typing

import pytest
from _pytest.fixtures import FixtureDef, SubRequest
from qtpy.QtWidgets import QMainWindow

from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.app.cli_options import get_options
from spyder.config.manager import CONF

if typing.TYPE_CHECKING:
    from spyder.api.plugin_registration.registry import SpyderPluginClass

__all__ = ["main_window_mock", "plugins_cls", "register_fixture"]


class MainWindowMock(QMainWindow):
    """QMainWindow mock for plugin tests."""

    def __init__(self):
        # This avoids using the cli options passed to pytest
        sys_argv = [sys.argv[0]]
        self._cli_options = get_options(sys_argv)[0]
        super().__init__()
        PLUGIN_REGISTRY.set_main(self)

    def register_plugin(self, plugin_class: type[SpyderPluginClass]):
        plugin = PLUGIN_REGISTRY.register_plugin(self, plugin_class)
        plugin._register()
        return plugin

    @staticmethod
    def unregister_plugin(plugin: SpyderPluginClass):
        assert PLUGIN_REGISTRY.delete_plugin(
            plugin.NAME
        ), f"{plugin.NAME} not deleted"
        plugin._unregister()

    @staticmethod
    def get_plugin(plugin_name, error=False):
        return PLUGIN_REGISTRY.get_plugin(plugin_name)

    @staticmethod
    def is_plugin_available(plugin_name):
        return PLUGIN_REGISTRY.is_plugin_available(plugin_name)


@pytest.fixture(scope="session")
def main_window_mock(qapp):
    """Create a QMainWindow mock for plugin tests."""

    window = MainWindowMock()

    try:
        yield window
    finally:
        CONF.reset_manager()
        PLUGIN_REGISTRY.reset()
        del window
        gc.collect()


@pytest.fixture(scope="session")
def plugins_cls() -> typing.Generator[
    typing.Iterable[typing.Tuple[str, type[SpyderPluginClass]]], None, None
]:
    """Fixture that yields the plugin's classes to be tested.

    before the yield statement, it will be run at startup.
    after the yield statement, it will be run at teardown.

    Yields:
        List[Tuple[str, type[SpyderPluginClass]]]: A list of fixture's names
                                                   and plugin's classes to
                                                   create a fixture for.
    Raises:
        NotImplementedError: This fixture must be implemented by the test.
    """
    raise NotImplementedError("This fixture must be implemented by the test.")


@pytest.fixture(scope="session", autouse=True)
def register_fixture(request: SubRequest, plugins_cls):
    """
    Dynamically adds fixture for registering plugins.
    """
    for fixture_name, plugin_cls in plugins_cls:
        # Create a factory function so each fixture gets its own function
        def register_plugin_factory(plugin_cls):
            def register_plugin(main_window_mock):
                plugin = main_window_mock.register_plugin(plugin_cls)
                try:
                    yield plugin
                finally:
                    main_window_mock.unregister_plugin(plugin)
            return register_plugin

        request._fixturemanager._arg2fixturedefs[fixture_name] = [
            FixtureDef(
                argname=fixture_name,
                func=register_plugin_factory(plugin_cls),
                scope="session",
                fixturemanager=request._fixturemanager,
                baseid=request.node.nodeid,
                params=None,
            )
        ]

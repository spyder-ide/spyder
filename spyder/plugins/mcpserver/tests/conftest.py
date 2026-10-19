# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Fixtures for the MCP server plugin tests."""

# Third-party imports
import pytest

# Local imports
from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY
from spyder.config.manager import CONF

# Reuse the IPython console fixture to test tools against real kernels
from spyder.plugins.ipythonconsole.tests.conftest import (  # noqa: F401
    ipyconsole,
    pytest_runtest_makereport,
)


@pytest.fixture
def main_window(qtbot):
    """Start a full Spyder window, with code analysis enabled."""
    CONF.set("tours", "show_tour_message", False)
    CONF.set("main", "single_instance", False)
    CONF.set("ipython_console", "pylab/backend", "inline")
    CONF.set("debugger", "pdb_stop_first_line", True)

    from spyder.app import start
    window = start.main()
    yield window

    window.closing(close_immediately=True)
    window.close()
    CONF.reset_to_defaults(notification=False)
    CONF.reset_manager()
    PLUGIN_REGISTRY.reset()

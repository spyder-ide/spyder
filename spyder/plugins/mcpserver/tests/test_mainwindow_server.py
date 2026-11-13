# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for running the MCP server in a full Spyder window."""

# Standard library imports
import json

# Third-party imports
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.config.manager import CONF


def test_server_restarts(main_window, qtbot):
    """The server restarts on the same port if it exits unexpectedly."""
    mcp_server = main_window.get_plugin("mcp_server")
    mcp_server.start_server()
    qtbot.waitUntil(mcp_server.is_server_running, timeout=30000)
    url = mcp_server.get_url()

    mcp_server._client._process.kill()
    qtbot.waitUntil(lambda: not mcp_server.is_server_running(), timeout=10000)
    qtbot.waitUntil(mcp_server.is_server_running, timeout=30000)
    assert mcp_server.get_url() == url

    # But not if it's stopped
    mcp_server.stop_server()
    qtbot.waitUntil(lambda: not mcp_server.is_server_running(), timeout=10000)
    qtbot.wait(2000)
    assert not mcp_server.is_server_running()


def test_server_kept_for_plugins(main_window, qtbot):
    """
    A server started by a plugin (e.g. for its agent sessions) keeps running
    when Spyder notifies the "enabled" option without a change, and when the
    user turns the option off.
    """
    mcp_server = main_window.get_plugin("mcp_server")
    assert not mcp_server.get_conf("enabled")
    mcp_server.start_server()
    qtbot.waitUntil(mcp_server.is_server_running, timeout=30000)

    # Spyder notifies all options, e.g. when the main interpreter is set
    CONF.notify_section_all_observers("mcp_server")
    qtbot.wait(2000)
    assert mcp_server.is_server_running()

    mcp_server.set_conf("enabled", True)
    mcp_server.set_conf("enabled", False)
    qtbot.wait(2000)
    assert mcp_server.is_server_running()

    # Users can copy the configuration to connect other agents to it
    mcp_server.copy_config()
    config = json.loads(QApplication.clipboard().text())
    assert config["mcpServers"]["spyder"] == {
        "type": "http",
        "url": mcp_server.get_url(),
        "headers": {
            "Authorization": f"Bearer {mcp_server.get_conf('token')}"
        },
    }

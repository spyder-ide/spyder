# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for managing the MCP server subprocess from Spyder."""

# Third-party imports
import pytest

# Local imports
from spyder.plugins.mcpserver.client import MCPServerClient
from spyder.utils.misc import select_port

pytest.importorskip("mcp")


def test_start_and_exits(qtbot):
    client = MCPServerClient(None, dict, lambda *args: None)
    ready, stopped = [], []
    client.sig_server_ready.connect(ready.append)
    client.sig_server_stopped.connect(stopped.append)

    # Starting again while it starts doesn't start a second server
    port = select_port(default_port=18868)
    client.start("127.0.0.1", port, "token")
    client.start("127.0.0.1", port + 1, "token")
    qtbot.waitUntil(lambda: bool(ready), timeout=30000)
    qtbot.wait(2000)
    assert ready == [f"http://127.0.0.1:{port}/mcp"]

    # Exits that weren't requested are reported as unexpected
    client._process.kill()
    qtbot.waitUntil(lambda: bool(stopped), timeout=10000)
    assert client.exited_unexpectedly
    assert client.url is None

    # Stopping it isn't
    client.start("127.0.0.1", port, "token")
    qtbot.waitUntil(lambda: len(ready) == 2, timeout=30000)
    client.stop()
    qtbot.waitUntil(lambda: len(stopped) == 2, timeout=10000)
    assert not client.exited_unexpectedly

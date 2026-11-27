# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the JSON-RPC bridge."""

# Standard library imports
import asyncio

# Third-party imports
import pytest

# Local imports
from spyder.plugins.mcpserver.bridge import BridgeError, JsonRpcPeer


def make_pipe():
    """Return the (readline, write) ends of an in-memory line pipe."""
    queue = asyncio.Queue()

    async def write(data):
        await queue.put(data)

    return queue.get, write


def make_peers(handlers_a=None, handlers_b=None):
    a_to_b_read, a_to_b_write = make_pipe()
    b_to_a_read, b_to_a_write = make_pipe()
    peer_a = JsonRpcPeer(b_to_a_read, a_to_b_write, handlers_a)
    peer_b = JsonRpcPeer(a_to_b_read, b_to_a_write, handlers_b)
    return peer_a, peer_b, b_to_a_write


def test_request_response():
    async def run():
        async def add(params):
            return params["a"] + params["b"]

        peer_a, peer_b, _ = make_peers(handlers_b={"add": add})
        tasks = [
            asyncio.create_task(peer_a.run()),
            asyncio.create_task(peer_b.run()),
        ]

        # Several requests in flight at the same time
        results = await asyncio.gather(
            *[peer_a.request("add", {"a": i, "b": 1}) for i in range(5)]
        )
        assert results == [1, 2, 3, 4, 5]

        for task in tasks:
            task.cancel()

    asyncio.run(run())


def test_errors_and_notifications():
    async def run():
        received = asyncio.Event()

        async def fail(params):
            raise RuntimeError("kaboom")

        async def ping(params):
            received.set()

        peer_a, peer_b, _ = make_peers(
            handlers_b={"fail": fail, "ping": ping}
        )
        tasks = [
            asyncio.create_task(peer_a.run()),
            asyncio.create_task(peer_b.run()),
        ]

        with pytest.raises(BridgeError, match="kaboom"):
            await peer_a.request("fail")

        with pytest.raises(BridgeError, match="Method not found"):
            await peer_a.request("unknown")

        await peer_a.notify("ping")
        await asyncio.wait_for(received.wait(), 5)

        for task in tasks:
            task.cancel()

    asyncio.run(run())


def test_pending_requests_fail_on_eof():
    async def run():
        async def never(params):
            await asyncio.Event().wait()

        peer_a, peer_b, b_to_a_write = make_peers(handlers_b={"never": never})
        task_a = asyncio.create_task(peer_a.run())
        task_b = asyncio.create_task(peer_b.run())

        request = asyncio.create_task(peer_a.request("never"))
        await asyncio.sleep(0.1)

        # Simulate the other end closing the stream
        await b_to_a_write(b"")
        with pytest.raises(BridgeError, match="closed"):
            await asyncio.wait_for(request, 5)

        await task_a
        task_b.cancel()

    asyncio.run(run())
